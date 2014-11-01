from django import dispatch
from django.conf import settings
from django.db import models
from django.db.models import signals as django_signals
from django.contrib.gis.db import models as gis_models
from django.utils.translation import ugettext_lazy as _

from nodewatcher.core.registry import fields as registry_fields, registration


class SSID(models.Model):
    """
    Network identitiy of a specific project.
    """

    project = models.ForeignKey('Project', related_name='ssids')
    purpose = models.CharField(max_length=50)
    default = models.BooleanField(default=False)
    bssid = registry_fields.MACAddressField(null=True, blank=True)
    essid = models.CharField(max_length=50)

    def __unicode__(self):
        return u'%s (%s)' % (self.essid, self.bssid)


@dispatch.receiver(django_signals.post_save, sender=SSID)
def ssid_updated(sender, instance, **kwargs):
    """
    Ensure that only one SSID inside a project is selected as default.
    """

    if instance.default:
        SSID.objects.exclude(pk=instance.pk).filter(
            project=instance.project,
            default=True,
        ).update(default=False)


class Project(models.Model):
    """
    This class represents a project. Each project can contains some
    nodes and is also assigned a default IP allocation pool.
    """

    name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    location = gis_models.PointField(null=True)

    # Pools linked to this project
    pools_core_ippool = models.ManyToManyField('core.IpPool', related_name='projects')

    def __unicode__(self):
        return self.name


def project_default(request=None):
    if request and hasattr(request.user, 'profile'):
        return request.user.profile.default_project
    else:
        projects = Project.objects.all()
        if projects.exists():
            try:
                return projects.get(name__iexact=(settings.NETWORK.get('DEFAULT_PROJECT', None) or ''))
            except Project.DoesNotExist:
                return projects[0]
        else:
            return None


class ProjectConfig(registration.bases.NodeConfigRegistryItem):
    """
    Describes the project a node belongs to.
    """

    project = registry_fields.ModelSelectorKeyField(Project)

    class RegistryMeta:
        form_weight = 2
        registry_id = 'core.project'
        registry_section = _("Project")
        registry_name = _("Basic Project")

registration.point('node.config').register_item(ProjectConfig)
