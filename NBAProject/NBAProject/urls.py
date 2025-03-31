"""
URL configuration for NBAProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from app import views
from django.contrib import admin
from django.urls import path

urlpatterns = [

    path('', views.home_page),
    path('admin/', admin.site.urls),
    

    #Funcionalidades Básicas
    path('jogadores/', views.list_jogadores),  # Lista todos os jogadores únicos
    path('equipas/', views.equipas_page),  # Render da página de equipas
    path('equipas/filter/', views.list_equipas),  # Lista todas as equipas
    path('temporadas/', views.list_temporadas, name='seasons'),  # Lista todas as temporadas
    path('participacoes/', views.list_participacoes),  # Lista todas as participações
    path('stats/geral/', views.stats_geral),  # Contagem global de jogadores, equipas, temporadas

    #Páginas de detalhe básicas

    # Jogadores
    path('jogadores/page/', views.players_page, name='players_page'),
    path('jogadores/filter/', views.filter_players, name='filter_players'),
    path('jogadores/countries/', views.get_player_countries, name='player_countries'),
    path('jogadores/schools/', views.get_player_schools, name='player_schools'),
    path('jogador/<str:id>/', views.pagina_jogador),  # Página de jogador com participações
    #este dqui é giro se o complementarmos com o timelinde dos jogadores bem como com o grafo tudo o que tiver nas intermedias e for jogador 

    path('equipa/<str:id>/', views.pagina_equipa),  # Página de equipa com jogadores por temporada
    path('temporada/<str:ano>/', views.pagina_temporada),  # Página de temporada com equipas e jogadores

    #Arenas
    path('arenas/', views.list_arenas, name="list_arenas"),  # Lista todas as arenas
    path('arena/<str:id>/', views.pagina_arena),  # Detalhe de uma arena
    path('mapa/arenas/', views.mapa_arenas, name="mapa_arenas"),  # Mapa interativo com arenas
    path('mapa/arenas/view/', views.page_mapa_arenas, name='mapa_arenas_view'),

    #Funcionalidades Intermediárias
    path('jogador/<str:id>/timeline/', views.timeline_jogador),  # Linha do tempo da carreira do jogador
    path('grafo/jogador/<str:id>/', views.grafo_jogador),  # Grafo: Jogador → Equipas → Temporadas
    path('jogador/<str:id>/companheiros/', views.companheiros_jogador),  # Companheiros na mesma época
    # path('participacoes/filtradas/', views.filtrar_participacoes),  # Participações filtradas por jogador e temporada

    #Funcionalidades Avançadas
    path('comparar/', views.comparar_jogadores),  # Comparação entre dois jogadores
    path('comparar_jogadores/', views.comparar_jogadores_template),  # Template para comparação de jogadores
    path("rede/jogadores/", views.rede_jogadores),
    path("rede/jogadores/expand/<path:player_id>/", views.expandir_jogador),
    path('stats/', views.stats),

    # Admin
    path('staff/login/', views.login_view, name='staff_login'),
    path('staff/logout/', views.logout_view, name='logout'),
    path('staff/jogadores/adicionar/', views.add_player, name='add_player'),
    path('staff/delete_player/<str:player_id>/', views.delete_player, name='delete_player'),
    path('staff/jogadores/update/', views.update_player, name='update_player'),

    
    #Funcionalidades Extras
    # path('sparql/', views.executar_sparql),  # Playground SPARQL
    # path('exportar/participacoes/', views.exportar_participacoes),  # Exportar participações em CSV/JSON
]