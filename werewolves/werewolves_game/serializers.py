from swampdragon.serializers.model_serializer import ModelSerializer

class NotificationSerializer(ModelSerializer):
	class Meta:
		model = 'werewolves_game.Notification'
		publish_fields = ['message']
'''
class LobbySerializer(ModelSerializer):
	class Meta:
		model = "werewolves_game.GameList"
		publish_fields('name')'''