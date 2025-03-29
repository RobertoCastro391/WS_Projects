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
from django.contrib import admin
from django.urls import path
from app import views

urlpatterns = [

    path('', views.home_page),
    path('admin/', admin.site.urls),
    

    #Funcionalidades Básicas
    path('jogadores/', views.list_jogadores),  # Lista todos os jogadores únicos
    path('equipas/', views.list_equipas),  # Lista todas as equipas únicas
    path('temporadas/', views.list_temporadas),  # Lista todas as temporadas
    path('participacoes/', views.list_participacoes),  # Lista todas as participações
    path('stats/geral/', views.stats_geral),  # Contagem global de jogadores, equipas, temporadas

    #Páginas de detalhe básicas
    path('jogador/<str:id>/', views.pagina_jogador),  # Página de jogador com participações
    #este dqui é giro se o complementarmos com o timelinde dos jogadores bem como com o grafo tudo o que tiver nas intermedias e for jogador 

    path('equipa/<str:id>/', views.pagina_equipa),  # Página de equipa com jogadores por temporada
    path('temporada/<str:ano>/', views.pagina_temporada),  # Página de temporada com equipas e jogadores

    #Arenas
    path('arenas/', views.list_arenas),  # Lista todas as arenas
    path('arena/<str:id>/', views.pagina_arena),  # Detalhe de uma arena
    path('mapa/arenas/', views.mapa_arenas),  # Mapa interativo com arenas

    #Funcionalidades Intermediárias
    path('jogador/<str:id>/timeline/', views.timeline_jogador),  # Linha do tempo da carreira do jogador
    path('grafo/jogador/<str:id>/', views.grafo_jogador),  # Grafo: Jogador → Equipas → Temporadas
    path('jogador/<str:id>/companheiros/', views.companheiros_jogador),  # Companheiros na mesma época
    # path('participacoes/filtradas/', views.filtrar_participacoes),  # Participações filtradas por jogador e temporada

    #Funcionalidades Avançadas
    path('comparar/', views.comparar_jogadores),  # Comparação entre dois jogadores
    path('rede/jogadores/', views.rede_jogadores),  # Rede de conexões entre jogadores
    path('stats/', views.stats),
    
    #Funcionalidades Extras
    # path('sparql/', views.executar_sparql),  # Playground SPARQL
    # path('exportar/participacoes/', views.exportar_participacoes),  # Exportar participações em CSV/JSON
]