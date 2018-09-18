import csv
import json
import os
import re
import string
from io import TextIOWrapper

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
            form_data = TextIOWrapper(request.FILES['input_file'].file, encoding='utf-8')

            if project.is_type_of(Project.SEQUENCE_LABELING):
                _, ext = os.path.splitext(request.FILES['input_file'].name)

                if ext.lower() == '.json':
                    shortcut_gen = self.shortcut_gen()
                    color_gen = self.color_gen()

                    for annot in json.load(form_data):
                        text = annot.get("text", "")
                        if not text:
                            continue

                        doc = Document(text=text, project=project)
                        doc.save()

                        annotations = []
                        for ent in annot.get("entities", []):
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
                                    document=doc, label=label,
                                    user_id=self.request.user.id,
                                    start_offset=ent['start'], end_offset=ent['end']
                                )
                            )
                        if annotations:
                            SequenceAnnotation.objects.bulk_create(annotations)
                else:
                    reader = csv.reader(form_data)
                    Document.objects.bulk_create([Document(
                        text=line[0].strip(),
                        project=project) for line in reader]
                    )
            else:
                reader = csv.reader(form_data)
                Document.objects.bulk_create([Document(
                    text=line[0].strip(),
                    project=project) for line in reader]
                )

            return HttpResponseRedirect(reverse('dataset', args=[project.id]))
        except:
            return HttpResponseRedirect(reverse('upload', args=[project.id]))

    def seq_annotations(self, project, doc, text, shortcut_gen, color_gen):
        annotations = []
        offset = 0

        for match in re.finditer(self.re_entity, text):
            groupdict = match.groupdict()
            annot = groupdict['text']
            annot_label = groupdict['label']

            try:
                label = project.labels.get(text=annot_label)
            except Label.DoesNotExist:
                label = Label.objects.create(
                    text=annot_label, project=project,
                    shortcut=next(shortcut_gen), background_color=next(color_gen)
                )

            start_offset = match.start() - offset
            end_offset = start_offset + len(annot)
            offset += len(match.group(0)) - len(annot)
            annotations.append(
                SequenceAnnotation(
                    document=doc, label=label, user_id=self.request.user.id,
                    start_offset=start_offset, end_offset=end_offset
                )
            )

        return annotations

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
        filename = '_'.join(project.name.lower().split())
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="{}.json"'.format(
            filename)
        dataset = [d.make_dataset() for d in docs]
        response.content = json.dumps(dataset, ensure_ascii=False, indent=4)
        return response


class DemoTextClassification(TemplateView):
    template_name = 'demo/demo_text_classification.html'


class DemoNamedEntityRecognition(TemplateView):
    template_name = 'demo/demo_named_entity.html'


class DemoTranslation(TemplateView):
    template_name = 'demo/demo_translation.html'
