# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import swampdragon.models


class Migration(migrations.Migration):

    dependencies = [
        ('werewolves_game', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('message', models.TextField()),
            ],
            bases=(swampdragon.models.SelfPublishModel, models.Model),
        ),
        migrations.RemoveField(
            model_name='todoitem',
            name='todo_list',
        ),
        migrations.DeleteModel(
            name='TodoItem',
        ),
        migrations.DeleteModel(
            name='TodoList',
        ),
    ]
