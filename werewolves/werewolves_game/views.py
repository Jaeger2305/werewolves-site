from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.template import RequestContext, loader
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render

from werewolves_game.server_scripting.game import *

from django.conf import settings
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

import datetime

def home_view(request):
    return render(request, 'werewolves_game/home.html', {'response':'it worked!'})

def lobby_view(request):
    response = ""

    request.session['has_session'] = True		#without some kind of session modification it forgets it on refresh
    response = request.session.session_key

    return render(request, 'werewolves_game/lobby.html', {'response':response})

def session_view(request):
	session_key = request.GET.get("session_key", False)
	if not session_key:
		return

	session = SessionStore(session_key=session_key)
	
	dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	session['last_activity'] = dt
	session.save()
	payload =  {
		"response":"Session expiry updated: "+str(session_key),
	}
	return JsonResponse(payload)


from django.views.generic import ListView
from .models import Notification

def notif_view(request):
	notification_list = Notification.objects.order_by('-pk')[:5]
	context = {'object_list':notification_list}
	return render(request, 'werewolves_game/home2.html', context)