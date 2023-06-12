from django.urls import include, path
from django.contrib import admin
from main import views
from django.views.generic import TemplateView
from django.urls import re_path
from django.views.static import serve
from django.conf import settings

urlpatterns = [
        path('', TemplateView.as_view(template_name='home.html'), name='index'),
        path('admin/', admin.site.urls),
        path('users/', include('users.urls')),
        path('new/', views.new_data, name='new'),
        path('mine_block/', views.mine_block, name='mine_block'),
        path('get_chain/', views.get_full_chain, name='get_chain'),
        path('valid_chain/', views.valid_blockchain, name='valid_chain'),
        path('connect_node/', views.connect_new_node, name='connect_node'),
        path('consensus/', views.consensus, name='consensus'),
        path('users_blocks/', views.users_blocks, name='users_blocks'),
        path('check_images/', views.check_images, name='check_images'),
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
        path('show_images/', views.show_images, name='show_images'),
    ]   


