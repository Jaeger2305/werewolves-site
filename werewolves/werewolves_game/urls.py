from django.conf.urls import url, patterns
from django.views.generic import TemplateView

from . import views

urlpatterns = [
	url(r'^$', views.home_view, name='home'),
	url(r'^home2/$', views.notif_view, name='home2'),
	url(r'^lobby/$', views.lobby_view, name='lobby'),
	url(r'^extend_session/$', views.session_view, name='session'),
]

'''urlpatterns = patterns('',
	url(r'^lobby/$', TemplateView.as_view(template_name='lobby.html'), name='lobby'),
)'''