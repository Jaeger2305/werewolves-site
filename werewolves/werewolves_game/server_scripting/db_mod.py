from django.db import connection

cursor = connection.cursor()

cursor.execute("UPDATE django_content_type SET app_label='werewolves_game' WHERE app_label='polls'")

cursor.execute("ALTER TABLE polls_modelName RENAME TO werewolves_game_modelName")

cursor.execute("ALTER TABLE polls_modelName RENAME TO werewolves_game_modelName")

cursor.execute("UPDATE django_content_type SET name='werewolves_game' where name='polls_modelName' AND app_label='<OldAppName>'")