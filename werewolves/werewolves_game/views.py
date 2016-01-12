from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext, loader
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render

from werewolves_game.server_scripting.game import *

import datetime

def home_view(request):
    return render(request, 'werewolves_game/home.html', {'response':'it worked!'})

def lobby_view(request):
    response = ""
    import ipdb;ipdb.set_trace()
    response = request.session.session_key

    return render(request, 'werewolves_game/lobby.html', {'response':response})

def session_view(request):
	#request.session.set_expiry(100)
	
	dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	#request.session['last_activity'] = dt
	return {
		"response":"Session expiry updated",
		"status":"success"
	}


from django.views.generic import ListView
from .models import Notification

def notif_view(request):
	notification_list = Notification.objects.order_by('-pk')[:5]
	context = {'object_list':notification_list}
	return render(request, 'werewolves_game/home2.html', context)