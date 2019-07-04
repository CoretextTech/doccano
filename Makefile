.PHONY: all
all: build

PYTHON ?= python3

export ROOT_DIR := $(realpath .)
export VIRTUAL_ENV_DIR := $(ROOT_DIR)/venv

export VERSION := 0.1.0
export REGION := us-east-1

export DOCKER_IMAGE := coretext/doccano
export DOCKER_REGISTRY := 508054367788.dkr.ecr.us-east-1.amazonaws.com

export AWS_ACCESS_KEY=$(shell sed -n 's/.*aws_access_key_id *= *\([^ ]*.*\)/\1/p' < ~/.aws/credentials)
export AWS_SECRET_ACCESS_KEY=$(shell sed -n 's/.*aws_secret_access_key *= *\([^ ]*.*\)/\1/p' < ~/.aws/credentials)

export ECS_CLUSTER := coretext-doccano-alb-cluster
export ECS_SERVICE := coretext-doccano-service

help:
	@echo
	@echo '  make clean'
	@echo '  make virtualenv'
	@echo '  make cleanenv'
	@echo '  make srv'
	@echo '  make'
	@echo '  make install'
	@echo '  make deployment'

.PHONY: clean
clean:
	rm -rf build dist *.egg-info
	find . -type f -name '*.pyc' -print0 | xargs -0 rm -f
	find . -type d -name '__pycache__' -print0 | xargs -0 rm -rf

.PHONY: virtualenv
virtualenv:
	virtualenv --python $(PYTHON) $(VIRTUAL_ENV_DIR)
	$(VIRTUAL_ENV_DIR)/bin/pip install -U pip

	@echo '================================================================'
	@echo 'You can now enable virtualenv with:'
	@echo '  source $(VIRTUAL_ENV_DIR)/bin/activate'
	@echo '================================================================'

.PHONY: cleanenv
cleanenv:
	deactivate
	rm -rf $(VIRTUAL_ENV_DIR)

.PHONY: srv
srv:
	cd app; python manage.py runserver

.PHONY: build
build:
	docker build -t $(DOCKER_IMAGE):latest -t $(DOCKER_IMAGE):$(VERSION) -f docker/Dockerfile .

.PHONY: install
install:
	docker run -d --rm -p 5000:5000 -e "AWS_ACCESS_KEY_ID=$(AWS_ACCESS_KEY)" -e "AWS_SECRET_ACCESS_KEY=$(AWS_SECRET_ACCESS_KEY)" -e "DATA_URL=s3://coretext-8997495341/doccano/db.sqlite" $(DOCKER_IMAGE):latest python manage.py runserver "0.0.0.0:5000"

.PHONE: repository
repository:
	aws ecr describe-repositories --repository-names $(DOCKER_IMAGE) --region $(REGION) 2>&1 || aws ecr create-repository --repository-name $(DOCKER_IMAGE) --region $(REGION)

.PHONY: push
push:
	make
	make repository

	docker tag $(DOCKER_IMAGE):latest $(DOCKER_REGISTRY)/$(DOCKER_IMAGE)
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE)

	docker tag $(DOCKER_IMAGE):$(VERSION) $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):$(VERSION)
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):$(VERSION)

.PHONY: deployment
deployment:
	make push
	aws ecs update-service --cluster $(ECS_CLUSTER) --service $(ECS_SERVICE) --force-new-deployment --region $(REGION)
