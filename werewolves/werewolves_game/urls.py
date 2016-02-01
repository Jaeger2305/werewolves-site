from django.conf.urls import url, patterns
from django.views.generic import TemplateView

from . import views

urlpatterns = [
	url(r'^$', views.home_view, name='home'),
	url(r'^lobby/$', views.lobby_view, name='lobby'),
	url(r'^extend_session/$', views.session_view, name='session'),
]