import datetime

from django.utils import timezone

from django.db import models
from swampdragon.models import SelfPublishModel
from werewolves_game.serializers import NotificationSerializer

class Notification(SelfPublishModel, models.Model):
	serializer_class = NotificationSerializer
	message = models.TextField()

'''
class GameList(SelfPublishModel, models.Model):
    serializer_class = LobbySerializer
    ready = models.BooleanField(default=False)
    name = models.CharField(max_length=100)
    g_round = models.IntegerField()

class Players(models.Model):
	name = models.CharField(max_length=100)
	game = models.ForeignKey(GameList)'''