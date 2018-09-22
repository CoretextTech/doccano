import bz2
import json
import os
import re
import string
from io import TextIOWrapper

import six
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin

from .permissions import SuperUserMixin
from .forms import ProjectForm
from .models import Document, Project, SequenceAnnotation, Label


class IndexView(TemplateView):
    template_name = 'index.html'


class ProjectView(LoginRequiredMixin, TemplateView):

    def get_template_names(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        return [project.get_template_name()]


class ProjectsView(LoginRequiredMixin, CreateView):
    form_class = ProjectForm
    template_name = 'projects.html'


class DatasetView(SuperUserMixin, LoginRequiredMixin, ListView):
    template_name = 'admin/dataset.html'
    paginate_by = 10

    def get_queryset(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        return project.documents.all()


class LabelView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/label.html'


class StatsView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/stats.html'


class GuidelineView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/guideline.html'


class DataUpload(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/dataset_upload.html'

    re_item = re.compile(r'\s*[-\*+]\s*(.+)')
    re_comment = re.compile(r'<!--[\s\S]*?--!*>', re.MULTILINE)
    re_entity = re.compile(r'\[(?P<text>[^\]]+)'
                           r'\]\((?P<label>\w*?)'
                           r'(?:\:(?P<value>[^)]+))?\)')

    def post(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=kwargs.get('project_id'))
        try:
            file = request.FILES['input_file'].file
            filename = request.FILES['input_file'].name
            _, ext = os.path.splitext(filename)

            if ext.lower() not in ('.json', '.bz2'):
                raise ValueError(ext)

            if ext.lower() == '.bz2':
                content = bz2.BZ2File(file).read().decode('utf-8').splitlines()
            else:
                content = TextIOWrapper(file, encoding='utf-8').readlines()

            shortcut_gen = self.shortcut_gen()
            color_gen = self.color_gen()

            for doc in content:
                if isinstance(doc, six.string_types):
                    doc = json.loads(doc)
                text = doc.get("text")
                if not text:
                    continue

                document = Document(text=text, project=project)
                document.save()

                if project.is_type_of(Project.SEQUENCE_LABELING):
                    annotations = []
                    for ent in doc.get("entities", []):
                        try:
                            label = project.labels.get(text=ent['entity'])
                        except Label.DoesNotExist:
                            label = Label.objects.create(
                                text=ent['entity'], project=project,
                                shortcut=next(shortcut_gen),
                                background_color=next(color_gen)
                            )
                        annotations.append(
                            SequenceAnnotation(
                                document=document, label=label,
                                user_id=self.request.user.id,
                                start_offset=ent['start'], end_offset=ent['end']
                            )
                        )
                    if annotations:
                        SequenceAnnotation.objects.bulk_create(annotations)

            return HttpResponseRedirect(reverse('dataset', args=[project.id]))
        except:
            return HttpResponseRedirect(reverse('upload', args=[project.id]))

    def shortcut_gen(self):
        for char in string.ascii_lowercase:
            yield char

    def color_gen(self):
        yield '#66ffcc'
        yield '#ffc34d'
        yield '#00e600'
        yield '#4d9900'
        yield '#8cd9b3'
        yield '#3399ff'
        yield '#ff5c33'
        yield '#b300b3'
        yield '#cccc00'
        yield '#751aff'
        yield '#ff8080'
        yield '#d279a6'
        yield '#6666cc'
        yield '#00e6e6'
        yield '#cc6600'


class DataDownload(SuperUserMixin, LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        project_id = self.kwargs['project_id']
        project = get_object_or_404(Project, pk=project_id)
        docs = project.get_documents(is_null=False).distinct()
        return self.jsonify(project, docs)

    def jsonify(self, project, docs, compression=True, lines=True):
        filename = '{}.json'.format('_'.join(project.name.lower().split()))
        if compression:
            filename += '.bz2'

        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        dataset = [d.make_dataset() for d in docs]

        if lines:
            content = '\n'.join([json.dumps(doc, ensure_ascii=False) for doc in dataset])
        else:
            content = json.dumps(dataset, ensure_ascii=False)

        if compression:
            content = bz2.compress(content.encode('utf-8', errors='ignore'))

        response.content = content
        return response


class DemoTextClassification(TemplateView):
    template_name = 'demo/demo_text_classification.html'


class DemoNamedEntityRecognition(TemplateView):
    template_name = 'demo/demo_named_entity.html'


class DemoTranslation(TemplateView):
    template_name = 'demo/demo_translation.html'
