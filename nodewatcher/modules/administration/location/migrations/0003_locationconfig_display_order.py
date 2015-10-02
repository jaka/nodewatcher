# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('location', '0002_locationconfig_annotations'),
    ]

    operations = [
        migrations.AddField(
            model_name='locationconfig',
            name='display_order',
            field=models.IntegerField(null=True),
        ),
    ]
