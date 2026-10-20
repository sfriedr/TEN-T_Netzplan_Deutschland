import json
import os
import sys
import mysql.connector
from mysql.connector import Error
import networkx as nx
from pathlib import Path
import matplotlib.image as mpimg
from matplotlib.text import Text
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import numpy as np
from typing import Optional, List, Set, Tuple, Dict
import math
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import Menu
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import random

script_dir = Path(__file__).parent
config_path = script_dir / "config.json"

try:
    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    DB_HOST = config.get("DB_HOST")
    DB_USER = config.get("DB_USER")
    DB_PASSWORD = config.get("DB_PASSWORD")
    DB_NAME = config.get("DB_NAME")

except FileNotFoundError:
    print(f"Fehler: Die Konfigurationsdatei '{config_path}' wurde nicht gefunden.")
    sys.exit(1)



knoten_list: list[dict[str, str | int | tuple[float, float]]] = [] #Enthält Knoten aus Datenbank List[Dict[str, Union[str, Tuple[float, float], Optional[int]]]]
kante_list: list[dict[str, str | int | tuple[float, float]]] = []  #Enthält Kanten aus Datenbank List[Dict[str, Union[str, int, Tuple[float, float]]]]
stadt_list: list[dict[str, str | int | tuple[float, float]]] = []  #Enthält Städteknoten aus Datenbank
hafen_list: list[dict[str, str | int | tuple[float, float]]] = []
flughafen_list: list[dict[str, str | int | tuple[float, float]]] = []



pos: Dict[str, Tuple[float, float]] = {}                 #Speichert alle Knoten und ihre zugehörigen Koordinaten als (Längengrad, Breitengrad) -> {'Berlin': (13.405, 52.52), 'Frankfurt': (8.63658, 50.12125), ...}
legendBox_visible: bool = False                          #Speichert, ob Legendenbox angezeigt wird.
on_node_clicked: bool = False                            #Speichert, ob auf eine Knoten geklickt wurde.
on_edge_clicked: bool = False                            #Speichert, ob auf Kante geklickt wurde.
clicked_node: Optional[str] = None                       #Speichert den geklickten Knoten  
clicked_edge: Optional[Tuple[str, str, int]] = None      #Speichert die geklickte Kante
recentNode: str                                          #Speichert zuletzt angeklickte Node
verwendete_zielknoten: List[str] = []                    #WICHTIG -> Dies muss wieder auf null gesetzt werden sobald in "startSimulation" die Schleife für einen Startknoten durchlaufen ist.
ausgewählteKanten_set: Set[Tuple[str, str, int]] = set() #Wenn Menu-Item "Kante(n) auswählen" angeklickt, werden alle nachfolgend angeklickt Kanten gespeichert. Eine Kante ist als Tupel mit (Knoten_1-ID, Knoten_2-ID, Kante-ID) gespeichert.
kante_auswahl_aktiv: bool = False                        #Speichert, ob Menu-Item "Kante(n) auswählen" angeklickt wurde
gelöschteKanten_set: Set[Tuple[str, str, int]] = set()   #Speichert Kanten, die aus dem Graph gelöscht wurden.
legend_icon_list: List[AnnotationBbox] = []              #Liste der Legenden-Icons
legend_icon_description_list: List[Text] = []            #Liste an Beschreibungen der Legenden-Icons und -Kanten
legend_edge_list: List[Rectangle] = []                   #Liste der Legenden-Kanten

MG = nx.MultiGraph()

legendBox_width = 0.2
legendBox_length = 0.47
legendBox_x = 0.8
legendBox_y = 0.5 - legendBox_length/2  # Damit Legendenbox höhenmäßig immer mittig ist. -> 0.265

legendTab_width = 0.02
legendTab_length = legendBox_length
legendTab_x = 0.98
legendTab_y = legendBox_y


nodeAttributeBox_width = 0.37
nodeAttributeBox_length = 0.4
nodeAttributeBox_x = 0.0
nodeAttributeBox_y = 0.6

"""
X = 0.0 → linke Kante des Plots
X = 1.0 → rechte Kante des Plots
Y = 0.0 → untere Kante des Plots
Y = 1.0 → obere Kante des Plots
"""
# y = 0.75 würde bedeuten, dass ab dem untersten Abschnitt des Plots, 75% der Gesamtlänge nach oben gegangen wird.

simulationsAusgeführt: bool = False
konstFürUmkehrwertVonMaxRestkapazität: int = None
sumAngebotVerteilt: int = 0
dictTransitknotenUndAngebot: dict[str, int] = {}
dictTransportmengeProVerbindungsart: dict[str, int] = {}


def connect_to_database():
    """
    Stellt eine Verbindung zur MySQL-Datenbank her.
    Gibt das Connection-Objekt zurück oder None bei Fehler.
    """
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        if connection.is_connected():
            print("Erfolgreich mit der Datenbank verbunden.")
            return connection

    except Error as e:
        print(f"Fehler beim Verbinden mit der Datenbank: {e}")
        return None



def disconnect_from_database(connection):
    """
    Trennt die Verbindung, falls sie existiert.
    """
    if connection is not None and connection.is_connected():
        connection.close()
        print("Datenbankverbindung wurde getrennt.")
    else:
        print("Es besteht keine aktive Verbindung.")




def load_knoten_from_database(connection):
    """
    Liest alle Knoten aus der Tabelle 'knoten' und gibt sie als Liste zurück.
    Prüft vorher, ob die Verbindung aktiv ist.
    """
    # Prüfen, ob Verbindung existiert und aktiv ist
    if connection is None or not connection.is_connected():
        print("Keine aktive Verbindung zur Datenbank. Knoten können nicht geladen werden.")
        return []

    cursor = connection.cursor()


    try:
        query = "SELECT name, längengrad, breitengrad, typ, kapazität, auslastung, angebot FROM knoten;"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        #Speichert Knoten in knoten_list:
        for name, längengrad, breitengrad, typ, kapazität, auslastung, angebot in rows:
            knoten_list.append({
                "Name": name,
                "pos": (float(längengrad), float(breitengrad)), #Macht aus (Decimal('13.405000'), Decimal('52.520000')) -> (13.405000, 52.520000)
                "Typ": typ,
                "Kapazität": kapazität,
                "Auslastung": auslastung,
                "Angebot": angebot,
            })
            if typ == 'Stadt':
                stadt_list.append({
                "Name": name,
                "pos": (float(längengrad), float(breitengrad)), #Macht aus (Decimal('13.405000'), Decimal('52.520000')) -> (13.405000, 52.520000)
                "Typ": typ,
                "Kapazität": kapazität,
                "Auslastung": auslastung,
                "Angebot": angebot,
            })
            if typ == 'Hafen':
                hafen_list.append({
                "Name": name,
                "pos": (float(längengrad), float(breitengrad)), #Macht aus (Decimal('13.405000'), Decimal('52.520000')) -> (13.405000, 52.520000)
                "Typ": typ,
                "Kapazität": kapazität,
                "Auslastung": auslastung,
                "Angebot": angebot,
            })
            if typ == 'Flughafen':
                flughafen_list.append({
                "Name": name,
                "pos": (float(längengrad), float(breitengrad)), #Macht aus (Decimal('13.405000'), Decimal('52.520000')) -> (13.405000, 52.520000)
                "Typ": typ,
                "Kapazität": kapazität,
                "Auslastung": auslastung,
                "Angebot": angebot,
            })
        print("Knoten erfolgreich aus Datenbank geladen.")
        # knoten_list -> [{'Name': 'BER', 'pos': (13.5006, 52.3622), 'Typ': 'Flughafen', 'Kapazität': 8867, 'Auslastung': 3210, 'Angebot': 3209}, ...]
        # stadt_list -> [{'Name': 'Berlin', 'pos': (13.405, 52.52), 'Typ': 'Stadt', 'Kapazität': 1378716, 'Auslastung': 1084651, 'Angebot': 294065}, ...]
        # hafen_list ->  [{'Name': 'Berlin-Westhafen', 'pos': (13.29, 52.534), 'Typ': 'Hafen', 'Kapazität': 1369849, 'Auslastung': 1081441, 'Angebot': 288408}, ...]
        # flughafen_list -> [{'Name': 'BER', 'pos': (13.5006, 52.3622), 'Typ': 'Flughafen', 'Kapazität': 8867, 'Auslastung': 3210, 'Angebot': 3209}, ...]

    except mysql.connector.Error as e:
        print(f"Fehler beim Laden der Knoten: {e}")
        return []

    finally:
        cursor.close()





def load_kanten_from_database(connection):
    """
    Liest alle Kanten aus der Tabelle 'kante' und gibt sie als Liste zurück.
    Prüft vorher, ob die Verbindung aktiv ist.
    """
    # Prüfen, ob Verbindung existiert und aktiv ist
    if connection is None or not connection.is_connected():
        print("Keine aktive Verbindung zur Datenbank. Kanten können nicht geladen werden.")
        return []

    cursor = connection.cursor()


    try:
        query = "SELECT startknoten_name, startknoten_längengrad, startknoten_breitengrad, endknoten_name, endknoten_längengrad, endknoten_breitengrad, " \
        "verbindungsart, kapazitätsgrenze, restkapazität, engpass FROM kante;"
        cursor.execute(query)
        rows = cursor.fetchall()

        #Speichert Kanten in kanten_list:
        for startknoten_name, startknoten_längengrad, startknoten_breitengrad, endknoten_nam, endknoten_längengrad, endknoten_breitengrad, verbindungsart, kapazitätsgrenze, restkapazität, engpass in rows:
            kante_list.append({
                "Start-Name": startknoten_name,
                "Start-Koordinaten": (float(startknoten_längengrad), float(startknoten_breitengrad)),
                "End-Name": endknoten_nam,
                "End-Koordinaten": (float(endknoten_längengrad), float(endknoten_breitengrad)),
                "Verbindungsart": verbindungsart,
                "Kapazitätsgrenze": kapazitätsgrenze,
                "Restkapazität": restkapazität,
                "Engpass": engpass
            })
        # kante_list -> [{'Start-Name': 'BER', 'Start-Koordinaten': (13.5006, 52.3622), 'End-Name': 'CGN', 'End-Koordinaten': (7.1428, 50.865), 'Verbindungsart': 'Luft', 'Kapazitätsgrenze': 6108, 'Restkapazität': 6108, 'Engpass': 0}, ...]
        print("Kanten erfolgreich aus Datenbank geladen.")

    except mysql.connector.Error as e:
        print(f"Fehler beim Laden der Kanten: {e}")
        return []

    finally:
        cursor.close()




def erstelle_konstante(connection):
    global konstFürUmkehrwertVonMaxRestkapazität
    """
    a
    """
    # Prüfen, ob Verbindung existiert und aktiv ist
    if connection is None or not connection.is_connected():
        print("Keine aktive Verbindung zur Datenbank. Konstante konnte nicht ermittelt werden.")
        return []

    cursor = connection.cursor()


    try:
        query = "SELECT max(restkapazität) FROM kante"
        cursor.execute(query)
        queryResult: Tuple[int] = cursor.fetchone()
        konstFürUmkehrwertVonMaxRestkapazität = queryResult[0] + 1000000
        print("Konstante erfolgreich ermittelt.")

    except mysql.connector.Error as e:
        print(f"Fehler beim Ermitteln der Konstante: {e}")
        return []

    finally:
        cursor.close()


conn = connect_to_database()

load_knoten_from_database(conn)
load_kanten_from_database(conn)
erstelle_konstante(conn)

disconnect_from_database(conn)



#<--------------------Code für Hintergrundkarte-------------------------------------------------------------------------------------------------
fig = plt.figure(figsize=(8, 7), dpi=80) #fig (=figure) ist Fenster (Breite, Höhe)
#dpi = dots per inch -> Höheher Wert führt zu höherer Auflösung und größeres Bild (weniger Ränder)
fig.canvas.manager.set_window_title("TEN-T Knoten (Fokusbereich Deutschland)") # Fenstertitel

ax = plt.axes([0, 0, 1, 1], projection=ccrs.PlateCarree()) #ax (=axis) ist Zeichenbereich für Karte in Fenster
#"Axe", weil Karte ist geografisches Koordinatensystem.
#[0, 0, 1, 1] -> [linke Kante exakt am linken Rand des Figure-Fensters, untere Kante exakt am unteren Rand, Breite = 100% des Fensters, Höhe = 100% des Fensters]


def karte_erstellen():
    # Deutschland-Ausschnitt festlegen.
    ax.set_extent([5.5, 15.5, 47.0, 55.5], crs=ccrs.PlateCarree()) #PlateCarree versteht Daten als (Longitude, Latitute)
    #ax.set_title("TEN-T Knoten (Fokusbereich Deutschland)") # Plottitel. STeht direkt mittig über dem Plot (ax)

    # Hintergrundkarte
    ax.add_feature(cfeature.LAND, alpha=0.3)
    ax.add_feature(cfeature.OCEAN, alpha=0.2)
    ax.add_feature(cfeature.BORDERS, linewidth=1)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.STATES, linewidth=0.3)

karte_erstellen()
#---------------------------------------------------------------------------------------------------------------------------------------------->



#--------------------------------Code für Menübar-----------------------------------------------------------------------------------------
root = tk.Tk() #Hauptfenster der Tkinter-Anwendung
root.title("TEN-T Knoten (Fokusbereich Deutschland)")

menubar = Menu(root) #Menübar, die an Hauptfenster gebunden wird.

#Funktion von "Datei" -> "Originales Netz wiederherstellen"
def menu_wiederherstellen():
    original_netz_wiederherstellen()

#Funktion von "Simulation" -> "Simulation starten"
def menu_simulation():
    startSimulation()

#Funktion von "Simulation" -> "Engpässe anzeigen"
def menu_engpass():
    zeigeEngpässe()

#Funktion von "Datei" -> "Beenden"
def menu_beenden():
    root.quit() #Schlie0en des Hauptfensters "root"

#Funktion "Auswahl" -> "Kante(n) auswählen"
def menu_kante_auswählen():
    global kante_auswahl_aktiv
    kante_auswahl_aktiv = True
    print("\nKanten-Auswahlmodus aktiviert - bitte Kante anklicken")

def menu_kantenauswahl_beenden():
    global kante_auswahl_aktiv
    kante_auswahl_aktiv = False
    print("Kanten-Auswahlmodus deaktiviert\n")

def menu_auswahl_anzeigen():
    zeige_auswahl()

def menu_kanten_entfernen():
    lösche_kanten()

def menu_prozentuale_kantenbelastung():
    zeigeKantenbelastungDiagramm()

def menu_Kantenauswahl_zurücksetzen():
    global ausgewählteKanten_set
    ausgewählteKanten_set.clear()
    print("Alle Auswahlen entfernt.")

def menu_info():
    messagebox.showinfo("Ersteller", "Dieses Programm wurde erstellt von:\nSebastian Friedrich\n201724312")

def menu_maxKnotenAngebot():
    zeigePieCHartZuAngeboten()

def menu_transiknoten():
    zeigeTransitknotenDiagramm()

def menu_transportanteile():
    zeigeTransportanteilProVerbindungsart()

datei_menu = Menu(menubar, tearoff=0) #Erzeugt Untermenü des Hauptmenüs - tearoff verhindert Abreißen
datei_menu.add_command(label="Originales Netz wiederherstellen", command=menu_wiederherstellen) #Führt Funktion "menu_neu" aus
datei_menu.add_separator()                            #Trennlinie zwischen Untermenü "Neu" und Untermenü "Beenden"
datei_menu.add_command(label="Programm Beenden", command=menu_beenden) #Führt Funktion "menu_beenden" aus
menubar.add_cascade(label="Datei", menu=datei_menu)  #Fügt Obermenü "Datei" der Menübar hinzu

sim_menu = Menu(menubar, tearoff=0)
sim_menu.add_command(label="Angebotsverteilung starten", command=menu_simulation)
sim_menu.add_separator()
sim_menu.add_command(label="Kante(n) entfernen", command=menu_kanten_entfernen)
#sim_menu.add_command(label="Kante(n) entfernen")
menubar.add_cascade(label="Simulation", menu=sim_menu)

anzeige_menu = Menu(menubar, tearoff=0)
anzeige_menu.add_command(label="Engpässe anzeigen", command=menu_engpass)
anzeige_menu.add_separator()
anzeige_menu.add_command(label="Prozentuale Kantenbelastung anzeigen", command=menu_prozentuale_kantenbelastung)
anzeige_menu.add_separator()
anzeige_menu.add_command(label="Angebote vor/nach Verteilung", command=menu_maxKnotenAngebot)
anzeige_menu.add_separator()
anzeige_menu.add_command(label="Transportanteile pro Verbindungsart", command=menu_transportanteile)
anzeige_menu.add_separator()
anzeige_menu.add_command(label="Durchgelaufendes Angebot pro Transitknoten", command=menu_transiknoten)
menubar.add_cascade(label="Anzeigen", menu=anzeige_menu)

ausw_menu = Menu(menubar, tearoff=0)
ausw_menu.add_command(label="Kante(n) auswählen", command=menu_kante_auswählen)
ausw_menu.add_command(label="Auswahl beenden", command=menu_kantenauswahl_beenden)
ausw_menu.add_command(label="Ausgewählte Kante(n) anzeigen", command=menu_auswahl_anzeigen)
ausw_menu.add_command(label="Kantenauswahl zurücksetzen", command=menu_Kantenauswahl_zurücksetzen)
menubar.add_cascade(label="Auswahl", menu=ausw_menu)

help_menu = Menu(menubar, tearoff=0)
help_menu.add_command(label="Info", command=menu_info)
menubar.add_cascade(label="?", menu=help_menu)

root.config(menu=menubar) #Benutze diese Menüleiste im Fenster

#---------------------------------------------------------------------------------------------------------------------------------------------->



#<-------------------Code zum Einfügen der Knoten aus knoten_list in Graph MG--------------------------------------------------------------------------------------------------
def lade_knoten_in_Graph():
    global pos
    for knoten in knoten_list:
        name = knoten["Name"]        # Knoten-ID
        attrs = {
            "Name": name,
            "pos": knoten["pos"],
            "Typ": knoten["Typ"],
            "Kapazität": knoten["Kapazität"],
            "Auslastung": knoten["Auslastung"],
            "Angebot": knoten["Angebot"]
        }
        MG.add_node(name, **attrs)

    pos = nx.get_node_attributes(MG, 'pos')

lade_knoten_in_Graph()
#-------------------------------------------------------------------------------------------------------------------------------------------->



#<------------------- Code für Icons laden--------------------------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
stadtIcon = mpimg.imread(BASE_DIR / "docs" / "Icons" / "Stadt_Kernnetz.png")
flughafenIcon = mpimg.imread(BASE_DIR / "docs" / "Icons" / "Flughafen_Kernnetz.png")
hafenIcon = mpimg.imread(BASE_DIR / "docs" / "Icons" / "Hafen_Kernnetz.png")

#stadtIcon = mpimg.imread("Icons/Stadt_Kernnetz.png")
#flughafenIcon = mpimg.imread("Icons/Flughafen_Kernnetz.png")
#hafenIcon = mpimg.imread("Icons/Hafen_Kernnetz.png")

#Methode: Zeichnen der Icons an Knotenposition.
def draw_icon(ax, xy, icon, zoom=0.06): #ax -> Karte, x -> Längengrad, y -> Breitengrad, icon, zoom
    imgagebox = OffsetImage(icon, zoom=zoom) #Verpackt Icon/Bild in plottbares Objekt
    ab = AnnotationBbox(imgagebox, xy, frameon=False, xycoords=ccrs.PlateCarree()._as_mpl_transform(ax)) #Icon an mit geographischen Koord. an Katenposition hängen.
    ax.add_artist(ab) # Bild mit Datenposition der Karte hinzufügen.
#-------------------------------------------------------------------------------------------------------------------------------------------->



#<-------------Code zum Zeichnen der Icons an Knotenposition----------------------------------------------------------------------------------
def zeichne_icon_an_knotenposition():
    global ax
    for _, attr in MG.nodes(data=True): #Knoten-ID wird übersprungen, weil nicht gebraucht.
        x, y = attr["pos"]
        knoten_typ = attr["Typ"]

        if knoten_typ == "Stadt":
            draw_icon(ax, (x, y), stadtIcon, zoom=0.07)
        elif knoten_typ == "Hafen":
            draw_icon(ax, (x, y), hafenIcon, zoom=0.07)
        elif knoten_typ == "Flughafen":
            draw_icon(ax, (x, y), flughafenIcon, zoom=0.07)


zeichne_icon_an_knotenposition()
#-------------------------------------------------------------------------------------------------------------------------------------------->



#<-------------------------- Code für Labels anders positionieren------------------------------------------------------------------------------
def zeichne_knotenlabels():
    # Städte: größere Schrift, leicht oberhalb
    for stadt in stadt_list:
        x, y = pos[stadt["Name"]]
        plt.text(x, y + 0.04, stadt["Name"], fontsize=12, horizontalalignment='center')

    # Flughäfen: kleinere Schrift, leicht unterhalb
    for flughafen in flughafen_list:
        x, y = pos[flughafen["Name"]]
        plt.text(x, y - 0.02, flughafen["Name"], fontsize=7, horizontalalignment='center')

    # Häfen: kleinere Schrift, leicht unterhalb
    for hafen in hafen_list:
        x, y = pos[hafen["Name"]]
        plt.text(x, y - 0.02, hafen["Name"], fontsize=7, horizontalalignment='center')

zeichne_knotenlabels()
#------------------------------------------------------------------------------------------------------------------------------------------->



#---------------------------Code für Kanten zeichnen----------------------------------------------------------------------------------------<
def lade_kanten_in_graph():
    for kante in kante_list:
        startname = kante["Start-Name"]
        startkoordinate = kante["Start-Koordinaten"]
        endname = kante["End-Name"]
        endkoordinate = kante["End-Koordinaten"]
        verbindungsart = kante["Verbindungsart"]
        kapazitätsgrenze = kante["Kapazitätsgrenze"]
        restkapazität = kante["Restkapazität"]
        engpass = kante["Engpass"]

        if verbindungsart == "Straße":
            MG.add_edge(startname, endname, Start_Name = startname, Startkoordinaten = startkoordinate, End_name = endname, Endkoordinate = endkoordinate, Kapazitätsgrenze = kapazitätsgrenze, Restkapazität = restkapazität, Engpass = engpass, Verbindungsart = verbindungsart, color="red")
        elif verbindungsart == "Schiene":
            MG.add_edge(startname, endname, Start_Name = startname, Startkoordinaten = startkoordinate, End_name = endname, Endkoordinate = endkoordinate, Kapazitätsgrenze = kapazitätsgrenze, Restkapazität = restkapazität, Engpass = engpass, Verbindungsart = verbindungsart, color="green")
        elif verbindungsart == "Wasser":
            MG.add_edge(startname, endname, Start_Name = startname, Startkoordinaten = startkoordinate, End_name = endname, Endkoordinate = endkoordinate, Kapazitätsgrenze = kapazitätsgrenze, Restkapazität = restkapazität, Engpass = engpass, Verbindungsart = verbindungsart, color="blue")
        elif verbindungsart == "Luft":
            MG.add_edge(startname, endname, Start_Name = startname, Startkoordinaten = startkoordinate, End_name = endname, Endkoordinate = endkoordinate, Kapazitätsgrenze = kapazitätsgrenze, Restkapazität = restkapazität, Engpass = engpass, Verbindungsart = verbindungsart, color="black")

lade_kanten_in_graph()



"""
Methode "zeichne_kanten" sorgt dafür, dass jede Kante je nach Verbindungsart mit einer anderen Farbe gezeichnet wird.
Außerdem wird geprüft, ob es mehrere Kanten zwischen zwei Knoten gibt. Wenn ja, wird die erste Kante
noch gerade gezeichnet und weitere Kanten werden mit einem sukzessiv höheren Radius gezeichnet.
Dieser Radius wird auch als neuer Attributwert in der Kante gespeichert.
"""
def zeichne_kanten():
    global ax #Sicherstellen, dass das ax der Karte genutzt wird.
    for u, v, k in MG.edges(keys=True): #(key=True) holt die Attribute der Kanten -> also z.B. die Farben
        # Farbe der Kante holen
        color = MG[u][v][k]["color"]

        edgesZwischenZweiNodes = MG[u][v]
        numberOfEdges = len(edgesZwischenZweiNodes)

        if numberOfEdges > 1:
            radius = k * 0.1     # jeder Key → eigener Radius
            MG[u][v][k]["Kantenradius"] = radius   #Speichern des Kantenradius als Attribut. Wird später für edge_clicked wichtig.
            nx.draw_networkx_edges(
                MG,
                pos,
                edgelist=[(u, v, k)],
                edge_color=color,
                connectionstyle=f'arc3,rad={radius}', #Krümmung beim Zeichnen setzen.
                ax=ax #Explizit auf die Karte zeichnen
            )
        else:
            MG[u][v][k]["Kantenradius"] = 0.0
            nx.draw_networkx_edges(
                MG,
                pos,
                edgelist=[(u, v, k)],
                edge_color=color,
                connectionstyle='arc3,rad=0',
                ax=ax
            )

zeichne_kanten()
#------------------------------------------------------------------------------------------------------------------------------------------->



#<----------------Code für interagierbare Legende-------------------------------------------------------------------------------------------
"""
X = 0.0 → linke Kante des Plots
X = 1.0 → rechte Kante des Plots
Y = 0.0 → untere Kante des Plots
Y = 1.0 → obere Kante des Plots
"""
# y = 0.75 würde bedeuten, dass ab dem untersten Abschnitt des Plots, 75% der Gesamtlänge nach oben gegangen wird.

# Rechteck für Legende
legend_box = patches.Rectangle((legendBox_x, legendBox_y), legendBox_width, legendBox_length, #(x-Koord., y-Koord.), Breite, Höhe,
                                transform=ax.transAxes,         # Rechteck in relativen Achsenkood. definieren.
                                edgecolor='black', facecolor='gray', alpha=0.9)
ax.add_patch(legend_box) #Legendenbox in Zeichenbereich der Karte (ax) einfügen.
legend_box.set_visible(False) #Legendenbox soll per default eingeklappt sein.

# Textinhalte / Icons platzieren
legend_title = ax.text(legendBox_x + 0.01, legendBox_y + legendBox_length - 0.01,
                      "Legende:",
                      fontsize=12, verticalalignment='top',
                      transform=ax.transAxes)
ax.add_artist(legend_title) #Fügt den Text dem Plot explizit hinzu, statt implizit mit "legend_title = ax.text(...)"
legend_title.set_visible(False)


# Kleiner sichtbarer Tab
legend_tab = patches.Rectangle((legendTab_x, legendTab_y), legendBox_width, legendBox_length, 
                                transform=ax.transAxes,
                                edgecolor='black', facecolor='gray')
ax.add_patch(legend_tab)



def draw_legend_icon(icon_data, x: float, y: float):
    imagebox = OffsetImage(icon_data, zoom=0.1) #Zoom von 0.1 auf das Icon
    ab = AnnotationBbox(imagebox, (x, y), frameon=False, xycoords='axes fraction')  #Icon mit relativen Achsen-Koord. außer Katenposition hängen.
    ax.add_artist(ab) # Bild mit Datenposition der Karte hinzufügen.
    legend_icon_list.append(ab)
    return ab



def kante_engpass(ax, x, y, width, height): #Erstellt ein mehrfarbiges Rechteck
    global legend_edge_list
    farben = ["red", "gray", "red", "gray", "red"]
    teilbreite = width / 5

    for i, farbe in enumerate(farben):
        rect = patches.Rectangle(
            (x + i * teilbreite, y),   # Startpunkt verschieben
            teilbreite,
            height,
            transform=ax.transAxes,
            edgecolor=None,
            facecolor=farbe
        )
        ax.add_patch(rect)
        legend_edge_list.append(rect)


def draw_legend_edge():
    global ax
    kante_straße = patches.Rectangle((legendBox_x+0.01, legendBox_y + legendBox_length - 0.235), 0.05, 0.01, 
                                transform=ax.transAxes,
                                edgecolor='red', facecolor='red')
    
    kante_schiene = patches.Rectangle((legendBox_x+0.01, legendBox_y + legendBox_length - 0.29), 0.05, 0.01, 
                                transform=ax.transAxes,
                                edgecolor='green', facecolor='green')
    
    kante_wasser = patches.Rectangle((legendBox_x+0.01, legendBox_y + legendBox_length - 0.345), 0.05, 0.01, 
                                transform=ax.transAxes,
                                edgecolor='blue', facecolor='blue')
    
    kante_luft = patches.Rectangle((legendBox_x+0.01, legendBox_y + legendBox_length - 0.4), 0.05, 0.01, 
                                transform=ax.transAxes,
                                edgecolor='black', facecolor='black')
    
    kante_engpass(ax, x=legendBox_x+0.01, y=legendBox_y + legendBox_length - 0.455, width=0.05, height=0.01)
    
    legend_edge_list.append(kante_straße)
    legend_edge_list.append(kante_schiene)
    legend_edge_list.append(kante_wasser)
    legend_edge_list.append(kante_luft)
    ax.add_patch(kante_straße)
    ax.add_patch(kante_schiene)
    ax.add_patch(kante_wasser)
    ax.add_patch(kante_luft)

    

def draw_legend_description(description: str, x: float, y: float):
    global ax
    legend_description = ax.text(x, y,
                      description,
                      fontsize=10,
                      transform=ax.transAxes)
    legend_icon_description_list.append(legend_description)


def delete_legend_icon():
    for icon in legend_icon_list:
        icon.set_visible(False)
    legend_icon_list.clear()


def delete_legend_edge():
    for legend_kante in legend_edge_list:
        legend_kante.set_visible(False)
    legend_edge_list.clear()


def delete_legend_description():
    for description in legend_icon_description_list:
        description.set_visible(False)
    legend_icon_description_list.clear()


# === Event-Handler ===
def on_click_legendbox(event):
    global legendBox_visible
    global ax

    if event.button == 1: # Wenn linke Maustaste gedrückt
        if not event.inaxes: # Wenn Klick nicht im Plotbereich geschehen
            return
        else: # Wenn Klick im Plotbereich geschehen
            inv = ax.transAxes.inverted() # ax.transAxes transformiert Axenkoordinaten in Pixelkoordinaten - inverted() dreht die Transformation um.
            """
            Pixel-Klick: (450, 220)
            Transformierter Klick: (0.32, 0.87)
            """
            x, y = inv.transform((event.x, event.y)) # x- und y-Koordinate des Klicks

            if legendBox_visible == False: # Wenn Legendenbox eingeklappt.
                # Prüfen, ob Klick innerhalb des Tab-Bereichs liegt.
                if (legendTab_x <= x <= legendTab_x + legendTab_width and
                    legendTab_y <= y <= legendTab_y + legendTab_length):
                    legendBox_visible = True
                    legend_tab.set_visible(False)
                    legend_box.set_visible(True)
                    legend_title.set_visible(True)
                    draw_legend_icon(stadtIcon, legendBox_x+0.03, legendBox_y + legendBox_length - 0.07)
                    draw_legend_icon(flughafenIcon, legendBox_x+0.03, legendBox_y + legendBox_length - 0.125) # + 0.055
                    draw_legend_icon(hafenIcon, legendBox_x+0.03, legendBox_y + legendBox_length - 0.18) # + 0.055
                    draw_legend_edge()
                    draw_legend_description("= Stadtknoten", legendBox_x + 0.06, legendBox_y + legendBox_length - 0.07)
                    draw_legend_description("= Flughafenknoten", legendBox_x + 0.06, legendBox_y + legendBox_length - 0.125)
                    draw_legend_description("= Hafenknoten", legendBox_x + 0.06, legendBox_y + legendBox_length - 0.18)
                    draw_legend_description("= Straße", legendBox_x + 0.06, legendBox_y + legendBox_length - 0.235)
                    draw_legend_description("= Schiene", legendBox_x + 0.06, legendBox_y + legendBox_length - 0.29)
                    draw_legend_description("= Wasserstraße", legendBox_x + 0.06, legendBox_y + legendBox_length - 0.345)
                    draw_legend_description("= Luft", legendBox_x + 0.06, legendBox_y + legendBox_length - 0.4)
                    draw_legend_description("= Engpass", legendBox_x + 0.06, legendBox_y + legendBox_length - 0.455)
                    fig.canvas.draw_idle() # Triggert das Neuzeichnen des Plots
            else: # Wenn Legendenbox ausgeklappt
                if (legendBox_x <= x <= legendBox_x + legendBox_width and
                legendBox_y <= y <= legendBox_y + legendBox_length): # Prüfen, ob Klick innerhalb des Legendenbox-Bereichs liegt.
                    legendBox_visible = False
                    legend_tab.set_visible(True)
                    legend_box.set_visible(False)
                    legend_title.set_visible(False)
                    delete_legend_icon()
                    delete_legend_edge()
                    delete_legend_description()
                    fig.canvas.draw_idle() # Triggert das Neuzeichnen des Plots


# === Verbindung mit Ereignis herstellen ===
fig.canvas.mpl_connect('button_press_event', on_click_legendbox)
# ---------------------------------------------------------------------------------------------------------------------------------->


#<--------------------Code für Node-Attribut-Box------------------------------------------------------------------------------------------
# Rechteck für Legende
node_and_edge_attributeBox = patches.Rectangle((nodeAttributeBox_x, nodeAttributeBox_y), nodeAttributeBox_width, nodeAttributeBox_length, #(x-Koord., y-Koord.), Breite, Höhe,
                                transform=ax.transAxes,         # Rechteck in relativen Achsenkood. definieren.
                                edgecolor='black', facecolor='gray', alpha=0.9)
ax.add_patch(node_and_edge_attributeBox) #Node-Attribut-Box in Zeichenbereich der Karte (ax) einfügen.
node_and_edge_attributeBox.set_visible(False) #Node-Attribut-Box soll per default eingeklappt sein.


node_or_edge_attributes_text = ax.text(
    nodeAttributeBox_x + 0.01,
    nodeAttributeBox_y + nodeAttributeBox_length - 0.01,
    "",  # Text zunächst leer
    fontsize=12,
    verticalalignment='top',
    transform=ax.transAxes,
    visible=False
)
ax.add_artist(node_or_edge_attributes_text)



def clean_and_format_string(s: str) -> str:
    return s.replace("{", "").replace("}", "").replace("'", "").replace(",", "\n")

def draw_nodeAttributes(s) -> Text:
    text = clean_and_format_string(str(s))
    node_or_edge_attributes_text.set_text(text) # Inhalt aktualisieren node_attributes_text.set_visible(True) return node_attributes_text

# INTERAKTIVE KNOTEN UND KANTEN

# ---- Hilfsfunktion: Prüfen, ob Klick in der Nähe eines Knotens ist ----
def check_node_hit(event):
    global ax
    if event.inaxes != ax:
        return None

    # Toleranzradius in Datenkoordinaten (ca. 0.1°)
    tol = 0.1

    for node, (x, y) in pos.items():
        if abs(event.xdata - x) < tol and abs(event.ydata - y) < tol:
            return node

    return None


# ---- Hilfsfunktion: Prüfen, ob Klick eine Kante trifft ----
def check_edge_hit(event):
    global ax
    if event.inaxes != ax or event.xdata is None or event.ydata is None:
        return None

    click = np.array([event.xdata, event.ydata])

    min_dist = 0.1
    hit_edge = None

    for u, v, k, data in MG.edges(keys=True, data=True):
        x1, y1 = pos[u]
        x2, y2 = pos[v]

        p = np.array([x1, y1])
        q = np.array([x2, y2])

        radius = data.get("Kantenradius", 0)

        # Länge des Segment-Vektors
        seg = q - p
        seg_len2 = np.dot(seg, seg)
        if seg_len2 == 0:
            continue

        if radius == 0:
            # Projektion des Klicks auf das Liniensegment (clamp t in [0,1])
            t = np.dot(click - p, seg) / seg_len2
            t = max(0.0, min(1.0, t))
            closest = p + t * seg
            dist = np.linalg.norm(click - closest)

        else:
            # Gebogene Kante (arc3,rad=radius)
            x1, y1 = p
            x2, y2 = q

            dx = x2 - x1
            dy = y2 - y1
            seg_len = np.hypot(dx, dy)
            if seg_len == 0:
                continue

            # Mittelpunkt
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2

            # Normalisierte Normale
            nx = -dy / seg_len
            ny = dx / seg_len

            # Matplotlib: offset = rad * 0.5 * segment_length
            offset = radius * 0.5 * seg_len

            # zwei mögliche Kontrollpunkte (links/rechts)
            candidates = [
                (mx + nx * offset, my + ny * offset),
                (mx - nx * offset, my - ny * offset)
            ]

            best_dist = 1e9

            for cx, cy in candidates:
                # Kontrollpunkte der kubischen Bezier
                P0 = np.array([x1, y1])
                P3 = np.array([x2, y2])
                Pc = np.array([cx, cy])

                P1 = P0 + 2/3 * (Pc - P0)
                P2 = P3 + 2/3 * (Pc - P3)

                t = np.linspace(0, 1, 140)
                B = (
                    ((1 - t)**3)[:, None] * P0 +
                    (3 * (1 - t)**2 * t)[:, None] * P1 +
                    (3 * (1 - t) * t**2)[:, None] * P2 +
                    (t**3)[:, None] * P3
                )

                d = np.min(np.hypot(B[:,0] - click[0], B[:,1] - click[1]))
                best_dist = min(best_dist, d)

            dist = best_dist

        if dist < min_dist:
            min_dist = dist
            hit_edge = (u, v, k)

    return hit_edge



# ---- Box und Text ein-/ausblenden ----
def show_attribute_box(data):
    node_and_edge_attributeBox.set_visible(True)
    node_or_edge_attributes_text.set_visible(True)
    node_or_edge_attributes_text.set_text(clean_and_format_string(str(data)))
    fig.canvas.draw_idle()

def hide_attribute_box():
    node_and_edge_attributeBox.set_visible(False)
    node_or_edge_attributes_text.set_visible(False)
    fig.canvas.draw_idle()


# ---- Hauptevent: Klickverarbeitung, wenn auf Knoten oder Kante geklickt wird ----
def on_click_nodes_edges(event):
    global clicked_node, clicked_edge

    # 1. Prüfen, ob Knoten getroffen
    node = check_node_hit(event) #Rostock ODER None
    if node is not None:
        clicked_node = node
        clicked_edge = None
        attrs = MG.nodes[node] #{'name': 'Rostock', 'pos': (12.0991, 54.0924), 'typ': 'Stadt', 'angebot': None, 'akt_lagerbestand': None, 'lagerbestandsgrenze': None} ODER keine Ausgabe.
        show_attribute_box(attrs)
        return

    # 2. Prüfen, ob Kante getroffen
    edge = check_edge_hit(event) #('Berlin', 'Rostock', 0) ODER None
    if edge is not None:
        clicked_edge = edge
        clicked_node = None
        u, v, k = edge
        attrs = MG[u][v][k] ##{'Start_Name': 'Berlin', 'Startkoordinaten': (13.405, 52.52), 'End_name': 'Rostock', 'Endkoordinate': (12.0991, 54.0924), 'Angebot_Übertragen': None, 'Kapazität': 15, 'Verbindungsart': 'Straße', 'color': 'red', 'Kantenradius': 0.0} ONDER keine Ausgabe.
        show_attribute_box(attrs)
        return

    # 3. Nichts getroffen → Box ausblenden
    hide_attribute_box()


#Event verbinden
fig.canvas.mpl_connect("button_press_event", on_click_nodes_edges)
#---------------------------------------------------------------------------------------------------------------------------------------->


def tooltips_zeichnen():
    global ax
    ax.add_patch(legend_tab)
    ax.add_patch(legend_box)
    ax.add_artist(legend_title)
    ax.add_patch(node_and_edge_attributeBox)
    ax.add_artist(node_or_edge_attributes_text)
    fig.canvas.draw_idle()



#------------------------------Code für Simulation der Angebotsverteilung im Netzwerk-----------------------------------------------------<
alleAusgehendenKantenVonAllenKnoten: List[Tuple[str, List[Tuple[str, str, int]]]] = [] #List[Knoten_1, [Knoten_1, Knoten_2, Kanten-ID, ...], ...] -> [('Berlin', [('Berlin', 'Leipzig', 0), ('Berlin', 'Leipzig', 1), ('Berlin', 'Rostock', 0), ('Berlin', 'Rostock', 1)]), ...]
for knoten in MG.nodes():
    alleAusgehendenKantenVonAllenKnoten.append((knoten, list(MG.edges(nbunch=knoten, keys=True))))


def berechne_eukl_distanz(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


"""
Ermittelt zu einem Startknoten einen Zielknoten, welcher am nähesten ist und dessen Lager noch nicht voll ist (akt_lagerbestand != lagerbestandsgrenze).
Wurde dieser Zielknoten bereits verwendet, wird der zweitnäheste Zielknoten gewählt usw.
Beachte: Die Knoten-ID ist ein str, nämlich der Name.
"""
def findeZielknoten(startknoten: Tuple[str, dict]) -> Optional[str]:
    #print("Starte Methode 'findeZielknoten'")
    startknoten_id: str = startknoten[0]
    startknoten_pos = startknoten[1]['pos']

    global verwendete_zielknoten

    distanz_list: List[Tuple[str, str, float]] = [] ##[[startknoten_id, zielknoten1_id, distanz], [startknoten_id, zielknoten2_id, distanz], ...]

    mögliche_zielknoten = list(MG.nodes(data=True)) ##[('Berlin', {'name': 'Berlin', 'pos': (13.405, 52.52), 'typ': 'Stadt', 'angebot': 35, 'akt_lagerbestand': None, 'lagerbestandsgrenze': None}), ...]
    mögliche_zielknoten = list(filter(lambda knoten: knoten[1].get('Auslastung') != knoten[1].get('Kapazität'),mögliche_zielknoten)) #Löscht alle Knoten, dessen Auslastung so groß ist wie deren Kapazität.
    #alle_knoten_liste = list(filter(lambda knoten: not (knoten[1].get('akt_lagerbestand') is not None and knoten[1].get('lagerbestandsgrenze') is not None and knoten[1].get('akt_lagerbestand') == knoten[1].get('lagerbestandsgrenze')), alle_knoten_liste)) #Löscht alle Knoten, dessen aktueller Lagerbestand so groß ist wie deren Lagerbestandsgrenze, außer Knoten, deren beide Werte 'None' ist.
    mögliche_zielknoten = list(filter(lambda knoten: knoten[0] != startknoten_id, mögliche_zielknoten)) #Löscht startknoten_id aus alle_knoten_liste.
    mögliche_zielknoten = list(filter(lambda knoten: knoten[0] not in verwendete_zielknoten, mögliche_zielknoten)) #Löscht aus alle_knoten_liste alle Knoten-IDs, die in verwendete_zielknoten enthalten sind.
    
    if len(mögliche_zielknoten) == 0:
        return None

    for zielknoten in mögliche_zielknoten:
        zielknoten_id = zielknoten[0]
        zielknoten_pos = zielknoten[1]['pos']
        distanz: float = berechne_eukl_distanz(startknoten_pos, zielknoten_pos)
        distanz_list.append((startknoten_id, zielknoten_id, distanz))

    ergebnis_zielknoten: str = min(distanz_list, key=lambda t: t[2])[1] ##Zielknoten_id des Zielknotens, welcher dem Startknoten am nahesten ist.
    verwendete_zielknoten.append(ergebnis_zielknoten)
    #print("Beende Methode 'findeZielknoten'")
    return ergebnis_zielknoten


#print("Test von 'findeZielknoten':")
#ergebnis: str = findeZielknoten(('Berlin', {'name': 'Berlin', 'pos': (13.405, 52.52), 'typ': 'Stadt', 'angebot': 35, 'akt_lagerbestand': 50, 'lagerbestandsgrenze': 60}))
#print("Zielknoten:", ergebnis) #Zielknoten: Leipzig



"""
'So soll die Ausgabe der Methode startSimulation aussehen'

--- Starte Angebotsverteiltung ---

Angebot von Knoten_A: ...
Menge ... verteilt an Knoten ... auf Route ...
Menge ... verteilt an Knoten ... auf Route ...
...
Angebot von Knoten_A vollständig/nicht vollständig verteilt.
Knoten_A hat insgesamt eine Menge von ... verteilt.

Angebot von Knoten_B: ...
Kein Pfad gefunden.
Keine weiteren Zielknoten verfügbar.

Angebot von Knoten_B vollständig/nicht vollständig verteilt.
Knoten_A hat insgesamt eine Menge von ... verteilt.

Angebot von ...
...

--- Angebotsverteilung beendet ---
"""
#-------------------------------------------------------------------------------------------------------------------------------------------



"""
Funktion bestimmt zu einem kürzesten Weg von Dijkstra die verwendeten Kanten.
Ist nötig, weil Dijkstra-Funktionen bei einem MG nicht angeben welche Kante
zwischen zwei Knoten benutzt wurde, wenn es dort mehrere gibt.
Input z.B. ['A', 'B', 'C']
Output: z.B. [('A', 'B', 0), ('B', 'C', 0)]
"""
def gibVollstAngabeVonOptWeg(path: list[str]) -> list[tuple[str, str, int]]:
    result: list[tuple[str, str, int]] = []
    for i in range(len(path)-1):
        u, v = path[i], path[i+1] # u = 'A', v = 'B'
    
        # Hole alle Kanten zwischen diesen beiden Knoten
        edges = MG[u][v]  # {0: {'weight': 1, 'Kantenradius': -0.1}, 1: {'weight': 2, 'Kantenradius': 0.1}}
    
        # Finde den Key mit dem kleinsten Gewicht
        best_key = min(edges, key=lambda k: edges[k]['Restkapazität'])
        result.append((u, v, best_key))
    return result

"""
Methode ermittelt die kleinste Restkapazität einer Kante eines übergebenen Pfades.
Input z.B. [('A', 'B', 0), ('B', 'C', 0)]
Output z.B. 1
"""
def gibMinRestkapazität(path: list[tuple[str, str, int]]) -> int:
    restkapazitäten: list[int] = []
    for kante in path:
        u, v, edgeKey = kante[0], kante[1], kante[2]
        restkapazitäten.append(MG.edges[u, v, edgeKey]['Restkapazität'])
    minRestkapazität: int = min(restkapazitäten)
    return minRestkapazität

"""
Methode ermitelt wie viel Angebot die Transitknoten eines Übertragungsweges durchlaufen haben.
[('A', 'B', 0), ('B', 'C', 1), ('C', 'D', 1), ('D', 'E', 0)] und 4 -> {'B': 4, 'C': 4, 'D': 4}
"""
def ermittelAngebotPerTransitknoten(vollstOptWeg: list[tuple[str, str, int]], übertragendesAngebot: int):
    global dictTransitknotenUndAngebot
    
    if len(vollstOptWeg) <= 3:
        for weg in vollstOptWeg:
            knoten1_id = weg[0]
            knoten2_id = weg[1]
            if knoten1_id in dictTransitknotenUndAngebot:
                # Key existiert: Addiere zum alten Wert
                dictTransitknotenUndAngebot[knoten1_id] += übertragendesAngebot
            else:
                # Key existiert nicht: Erstelle ihn neu
                dictTransitknotenUndAngebot[knoten1_id] = übertragendesAngebot
            if knoten2_id in dictTransitknotenUndAngebot:
                # Key existiert: Addiere zum alten Wert
                dictTransitknotenUndAngebot[knoten2_id] += übertragendesAngebot
            else:
                # Key existiert nicht: Erstelle ihn neu
                dictTransitknotenUndAngebot[knoten2_id] = übertragendesAngebot
        return

    del vollstOptWeg[0]  #Erstes Tupel aus Liste löschen
    del vollstOptWeg[-1] #Letztes Tupel aus Liste löschen
    for weg in vollstOptWeg:
        knoten1_id = weg[0]
        knoten2_id = weg[1]
        if knoten1_id in dictTransitknotenUndAngebot:
            # Key existiert: Addiere zum alten Wert
            dictTransitknotenUndAngebot[knoten1_id] += übertragendesAngebot
        else:
            # Key existiert nicht: Erstelle ihn neu
            dictTransitknotenUndAngebot[knoten1_id] = übertragendesAngebot
        if knoten2_id in dictTransitknotenUndAngebot:
            # Key existiert: Addiere zum alten Wert
            dictTransitknotenUndAngebot[knoten2_id] += übertragendesAngebot
        else:
            # Key existiert nicht: Erstelle ihn neu
            dictTransitknotenUndAngebot[knoten2_id] = übertragendesAngebot


# Methode ermittelt pro Verbindungsart die absolute übertragene Transportmenge
# Ausgabe -> {'Straße': 100, 'Schiene': ...}
def ermittleTransportmengeProVerbindungsart(vollstOptWeg: list[tuple[str, str, int]], übertragendesAngebot: int):
    global dictTransportmengeProVerbindungsart # dict[str, int]
    for weg in vollstOptWeg:
        u = weg[0] #Knoten1-ID
        v = weg[1] #Knoten2-ID
        k = weg[2] #Kante-ID
        verbindungsart = MG.edges[u, v, k].get("Verbindungsart")
        if verbindungsart in dictTransportmengeProVerbindungsart:
            # Key existiert: Addiere zum alten Wert
            dictTransportmengeProVerbindungsart[verbindungsart] += übertragendesAngebot
        else:
            # Key existiert nicht: Erstelle ihn neu
            dictTransportmengeProVerbindungsart[verbindungsart] = übertragendesAngebot




#<-------------------------------------------------------------------------------------------------------------------------------------------<
def startSimulation():
    global konstFürUmkehrwertVonMaxRestkapazität
    global simulationsAusgeführt
    global sumAngebotVerteilt # Hat nichts mit Angebotsverteilung zu tun. - Wird später nur für Methode "zeigePieCHart" benötigt.

    knotenList = list(MG.nodes(data=True))
    random.shuffle(knotenList)

    print()
    print("--- Starte Angebotsverteilung ---")
    print()
    #print("Test1:\n", MG.nodes(data=True))         # [('BER', {'Name': 'BER', 'pos': (13.5006, 52.3622), 'Typ': 'Flughafen', 'Kapazität': 8867, 'Auslastung': 3210, 'Angebot': 3209}), ...]
    #print("\nTest2:\n", list(MG.nodes(data=True))) # [('BER', {'Name': 'BER', 'pos': (13.5006, 52.3622), 'Typ': 'Flughafen', 'Kapazität': 8867, 'Auslastung': 3210, 'Angebot': 3209}), ...]
    #Jeder Knoten im Graph wird durchlaufen und als Startknoten behandelt, welcher sein Angebot verteilen soll.
    for knoten in knotenList: # knoten z.B. -> ('Berlin', {'name': 'Berlin', 'pos': (13.405, 52.52), 'typ': 'Stadt', 'angebot': 35, 'akt_lagerbestand': 50, 'lagerbestandsgrenze': 60})
        startknoten: str = knoten[0]
        angebotStartknoten: int = knoten[1]["Angebot"]
        initialAngebotStartknoten: int = angebotStartknoten
        print()
        print()
        print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        print("Angebot von ", startknoten, ": ", angebotStartknoten)
        print()
        while angebotStartknoten > 0:
            zielknoten: Optional[str] = findeZielknoten(knoten)

            if zielknoten is None:
                #print("Keine weiteren Zielknoten verfügbar für:", startknoten)
                print("Keine weiteren Zielknoten verfügbar für", startknoten, ".\nKein Weg für Angebotsübertragung.")
                break

            restkapazitätZielknoten : int = (MG.nodes[zielknoten]["Kapazität"]) - (MG.nodes[zielknoten]["Auslastung"])
            

            try:
                optWeg: list[str] = nx.dijkstra_path(G=MG, source=startknoten, target=zielknoten, weight=lambda u, v, d: konstFürUmkehrwertVonMaxRestkapazität - d.get('Restkapazität', 0))
            except nx.NetworkXNoPath as e:
                #print("Kein optimaler Pfad von", startknoten, "zu", zielknoten, "gefunden.")
                continue #Springt zurück zu Anfang von while-Schleife


            vollstOptWeg: list[tuple[str, str, int]] = gibVollstAngabeVonOptWeg(optWeg)
            minKantenRestkapazitätVonOptWeg: int = gibMinRestkapazität(vollstOptWeg)


            if minKantenRestkapazitätVonOptWeg == 0:
                #print("Kein nutzbarer Transportweg von", startknoten, "zu", zielknoten)
                continue

            übertragendesAngebot: int = min(angebotStartknoten, minKantenRestkapazitätVonOptWeg, restkapazitätZielknoten)

            print("Menge ", übertragendesAngebot, "verteilt an Knoten ", zielknoten, " auf Route ", vollstOptWeg)
            angebotStartknoten -= übertragendesAngebot


            #[======Jedes Mal, wenn ein Angebot/Teilangebot verteilt wird, müssen im Graphen die Knoten & Kanten mit ihren Attributen entsprechend angepasst werden.======]
            #Knoten-Attribut "angebot", "akt_lagerbestand" anpassen
            MG.nodes[startknoten]["Angebot"] = angebotStartknoten
            MG.nodes[startknoten]["Auslastung"] -= übertragendesAngebot
            MG.nodes[zielknoten]["Auslastung"] += übertragendesAngebot

            #Kanten-Attribut "Restkapazität" & "Engpass" anpassen
            for kante in vollstOptWeg:
                MG.edges[kante]["Restkapazität"] -= übertragendesAngebot
                if MG.edges[kante]["Restkapazität"] == 0:
                    MG.edges[kante]["Engpass"] = 1
            #[==================================================================================================]

            sumAngebotVerteilt += übertragendesAngebot # Hat nichts mit Angebotsverteilung zu tun. - Wird später nur für Methode "zeigePieCHart" benötigt.
            ermittelAngebotPerTransitknoten(vollstOptWeg, übertragendesAngebot) # Hat nichts mit Angebotsverteilung zu tun. - Wird für eine ander Funktion benötigt.
            ermittleTransportmengeProVerbindungsart(vollstOptWeg, übertragendesAngebot) # Hat nichts mit Angebotsverteilung zu tun. - Wird für eine ander Funktion benötigt.

        if angebotStartknoten != 0:
            print()
            print("Angebot von Knoten ", startknoten, " nicht vollständig verteilt.")
            print("Knoten ", startknoten, " hat insgesamt eine Menge von ", initialAngebotStartknoten - angebotStartknoten, "verteilt.")
            print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        else:
            print()
            print("Angebot von Knoten ", startknoten, " vollständig verteilt.")
            print("Knoten ", startknoten, " hat insgesamt eine Menge von ", initialAngebotStartknoten - angebotStartknoten, "verteilt.")
            print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

        global verwendete_zielknoten
        verwendete_zielknoten = []
        simulationsAusgeführt = True
    print()
    print()
    print("--- Angebotsverteilung beendet ---")
    print()
    print()
#-------------------------------------------------------------------------------------------------------------------------------------------->




#<------------------------Code zum Anzeigen von Engpässen------------------------------------------------------------------------------------<
"""
Methode zeichnet Engpässe auf Netzkarte,
zeigt Quote von Engpässen in Konsole
"""
def zeigeEngpässe():
    global simulationsAusgeführt
    
    if simulationsAusgeführt == False:
        messagebox.showwarning("Simulations nicht ausgeführt", "Führen Sie vorher einmal die Simulation aus, um sich die prozentuale Kantenbelastung anzeigen zu lassen.")
        return
    
    global ax
    engpassListe: List[Tuple[str, str, int]] = []
    anzahlKanten: int = MG.number_of_edges()
    anzahlEngpässe: int = 0
    anzahlEngpassStraße: int = 0
    anzahlEngpassSchiene: int = 0
    anzahlEngpassWasser: int = 0
    anzahlEngpassLuft: int = 0

    ax.clear()
    karte_erstellen()
    zeichne_icon_an_knotenposition()
    zeichne_knotenlabels()
    #zeichne_kanten()
    tooltips_zeichnen()

    for u, v, k, attr in MG.edges(keys=True, data=True): #attr ist das Dictionary mit den Kanten-Attributen
        farbe = attr.get("color")
        radius = attr.get("Kantenradius")
        engpass = attr.get("Engpass")
        verbindungsart = attr.get("Verbindungsart")

        if engpass == 1:
            engpassListe.append((u, v, k))
            nx.draw_networkx_edges(
                MG,
                pos,
                edgelist=[(u, v, k)],
                edge_color="red",
                style="dotted",
                width=3.0,
                connectionstyle=f"arc3,rad={radius}"
            )
            anzahlEngpässe += 1
            if verbindungsart == 'Straße':
                anzahlEngpassStraße += 1
            elif verbindungsart == 'Schiene':
                anzahlEngpassSchiene +=1
            elif verbindungsart == 'Wasser':
                anzahlEngpassWasser += 1
            elif verbindungsart == 'Luft':
                anzahlEngpassLuft += 1
        else:
            nx.draw_networkx_edges(
                MG,
                pos,
                edgelist=[(u, v, k)],
                edge_color=farbe,
                connectionstyle=f"arc3,rad={radius}"
            )

    if len(engpassListe) == 0:
        print("Es gibt keine Engpässe.")
    else:
        print("Die Engpässe lauten:")
        for engpass in engpassListe:
            print(engpass)
        
        engpassquote: float = (anzahlEngpässe * 100) / anzahlKanten
        engpassquote = round(engpassquote, 2)

        

        print(f"----\nEngpässe machen {engpassquote}% der Kanten aus.")
        print("Davon sind ...")
        print(f"   {round(((anzahlEngpassStraße * 100) / anzahlEngpässe), 2)}% Straße")
        print(f"   {round(((anzahlEngpassSchiene * 100) / anzahlEngpässe), 2)}% Schiene")
        print(f"   {round(((anzahlEngpassWasser * 100) / anzahlEngpässe), 2)}% Wasser")
        print(f"   {round(((anzahlEngpassLuft * 100) / anzahlEngpässe), 2)}% Luft")
    
    fig.canvas.draw_idle()
#-------------------------------------------------------------------------------------------------------------------------------------------->





#--------------------------------Code für Kanten auswählen-----------------------------------------------------------------------------------<

def wähle_kante(event):
    global ausgewählteKanten_set, kante_auswahl_aktiv

    if not kante_auswahl_aktiv:
        return  # normaler Klick, nichts tun

    edge = check_edge_hit(event) #(Knoten1-ID, Knoten2-ID, Kante-ID)
    if edge is not None and edge not in ausgewählteKanten_set:
        ausgewählteKanten_set.add(edge)
        print("Kante der Auswahl hinzugefügt:", edge)
    elif edge is not None and edge in ausgewählteKanten_set:
        ausgewählteKanten_set.remove(edge)
        print("Kante der Auswahl entfernt:", edge)

fig.canvas.mpl_connect("button_press_event", wähle_kante)
#-------------------------------------------------------------------------------------------------------------------------------------------->





#--------------------------------------------------------------------------------------------------------------------------------------------<
# Funktion zum Öffnen des Anzeige-Fensters
def zeige_auswahl():
    # Neues Fenster
    fenster = tk.Toplevel(root)
    fenster.title("Ausgewählte Kante(n)")
    fenster.geometry("800x350")
    
    # Treeview (Tabelle)
    tree = ttk.Treeview(fenster, columns=("A", "B", "C"), show="tree headings", selectmode="extended")
    tree.heading("A", text="Knoten_1-ID")
    tree.heading("B", text="Knoten_2-ID")
    tree.heading("C", text="Kanten-ID")

    # Einträge aus dem Set hinzufügen
    for kante in ausgewählteKanten_set:
        tree.insert("", tk.END, values=kante)
    
    tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)


    # Button für Löschen ausgewählter Zeilen
    btn_auswahl_löschen = tk.Button(fenster, text="Kante abwählen",
                                    command=lambda: lösche_auswahl(tree, ausgewählteKanten_set))
    btn_auswahl_löschen.pack(pady=5)

    # Button für Alles löschen
    btn_alle_loeschen = tk.Button(fenster, text="Alles abwählen",
                                  command=lambda: lösche_alles(tree, ausgewählteKanten_set))
    btn_alle_loeschen.pack(pady=5)
    
    

# Funktion zum Löschen einer ausgewählten Kante
def lösche_auswahl(tree, ausgewählteKanten_set):
    selected = tree.selection() #Speichert Zeilen-IDs "iid" der Ausgewählten Zeilen in einem Tupel. -> ('I002', 'I003')
    if not selected:
        messagebox.showwarning("Keine Auswahl", "Bitte wähle ein Element aus.")
        return
        
    for iid in selected:
        kante = tree.item(iid, "values") #Speichert Zeilenwert einer ausgewählten Spalten-ID als Tupel. -> ('Berlin', 'Rostock', '0')
        kante = (kante[0], kante[1], int(kante[2])) #TreeView speichert Zeilen immer als Strings. Darum ('Berlin', 'Rostock', '0') zu ('Berlin', 'Rostock', 0) konvertieren.

        if kante in ausgewählteKanten_set:
            ausgewählteKanten_set.remove(kante)
            tree.delete(iid)
            print("Kante aus Auswahl entfernt:", kante)

##pack, grid, place

# Funktion zum Löschen der gesamten Auswahl an Kanten
def lösche_alles(tree, ausgewählteKanten_set):
    zeilen_id_tupel: Tuple[str, ...] = tree.get_children()
    if len(zeilen_id_tupel) == 0:
        messagebox.showwarning("Keine Zeilen vorhanden", "Fügen Sie vorher erst Kanten der Auswahl hinzu bevor Sie wieder welche abwählen möchten.")
        return
    
    for iid in zeilen_id_tupel:
        kante = tree.item(iid, "values")
        kante = (kante[0], kante[1], int(kante[2]))
        if kante in ausgewählteKanten_set:
            ausgewählteKanten_set.remove(kante)
        tree.delete(iid)
    print("Alle Auswahlen entfernt.")
#-------------------------------------------------------------------------------------------------------------------------------------------->




#-------------------------------------------------------------------------------------------------------------------------------------------->
def lösche_kanten():
    global ax
    #Prüfen, dass Auswahl vorher beendet sein muss.
    if kante_auswahl_aktiv == True:
        messagebox.showwarning("Kanten-Auswahlmodus noch aktiv", "Bitte beenden Sie vorher den Kanten-Auswahlmodus,\nbevor Sie Kanten löschen.")
    elif len(ausgewählteKanten_set) == 0:
        messagebox.showwarning("Keine Auswahl", "Sie müssen Kanten ausgewählt haben, um sie löschen zu können.")
    else:
        ax.clear()
        print("-------")
        for kante in ausgewählteKanten_set.copy(): #Über Kopie wird iteriert, während Original verändert wird. -> Verhindert Fehler "RuntimeError: Set changed size during iteration"
            u, v, k = kante
            if MG.has_edge(u, v, k):
                MG.remove_edge(u, v, k)
                gelöschteKanten_set.add(kante)
                ausgewählteKanten_set.remove(kante)
                print("Kante", kante, "gelöscht.")
        print("-------")
        karte_erstellen()
        zeichne_icon_an_knotenposition()
        zeichne_knotenlabels()
        zeichne_kanten()
        tooltips_zeichnen()




def original_netz_wiederherstellen():
    global simulationsAusgeführt
    global ax
    global sumAngebotVerteilt
    global dictTransitknotenUndAngebot
    global dictTransportmengeProVerbindungsart
    sumAngebotVerteilt = 0
    simulationsAusgeführt = False
    dictTransitknotenUndAngebot.clear()
    dictTransportmengeProVerbindungsart.clear()

    ax.clear()
    MG.clear()
    lade_knoten_in_Graph()
    lade_kanten_in_graph()

    karte_erstellen()
    zeichne_icon_an_knotenposition()
    zeichne_knotenlabels()
    zeichne_kanten()
    tooltips_zeichnen()
    fig.canvas.draw_idle()
    print("\nOriginalnetz wiederhergestellt\n")



#Methode erstellt ein Balkendiagramm zum Darstellen der prozentualen Auslastungen der Kanten
def zeigeKantenauslastungDiagramm_2():
    global simulationsAusgeführt

    if simulationsAusgeführt == False:
        messagebox.showwarning("Simulations nicht ausgeführt", "Führen Sie vorher einmal die Simulation aus, um sich die prozentuale Kantenbelastung anzeigen zu lassen.")
        return

    height: list[int] = []           # Enthählt die Auslastungen
    #bars: list[tuple[str, str]] = [] # Enthält die Kanten (Knoten1_ID, Knoten2_ID)
    bars: list[str] = []

    for u, v, _,  attr in MG.edges(keys=True, data=True):
        kapazitätsgrenze = attr.get("Kapazitätsgrenze")
        restkapazität = attr.get("Restkapazität")
        auslastung = kapazitätsgrenze - restkapazität
        auslastungProzent = (auslastung * 100)/kapazitätsgrenze
        auslastungProzent = round(auslastungProzent, 2)

        height.append(auslastungProzent)

        bars.append(u + "-" + v)
        #bars.append((u, v))

    df = pd.DataFrame({
        'Kante': bars,
        'Auslastung': height
    })
    df = df.sort_values(by=['Auslastung'], ascending=True)
    anzahl_kanten = len(df)


    fenster = tk.Toplevel(root) # Warum Toplevel?
    fenster.title("Prozentuale Belastung jeder Kante")
    fenster.geometry("1300x1000") # Größenangabe: X-Achse x y-Achse

    
    canvas = tk.Canvas(fenster) # Erzeugt Zeichenbereich, weil Tkinter Frames nicht scrollen kann.
    scrollbar = tk.Scrollbar(fenster, orient="vertical", command=canvas.yview) #Erzeugung von Scrollbar und Festlegung der Scrollrichtung
    canvas.configure(yscrollcommand=scrollbar.set) # Verbdinung von Canvas-Zeichenbereich und Scrollbar.

    scrollbar.pack(side="right", fill="y") # Positionierung der Scrollbar und vertikale Füllung der Bar des Fensters.
    canvas.pack(side="left", fill="both", expand=True)

    container = tk.Frame(canvas) # Ersetellen von Container in Zeichenbereich, in welchem Diagramm kommmen soll.
    canvas.create_window((0, 0), window=container, anchor="nw") # Positionieren des Containers im Zeichenbereich Canvas.

    
    #fig_barplot, ax_barplot = plt.subplots(
     #   figsize=(8, max(6, anzahl_kanten * 0.4)) # Erstellen von Diagramm und Größe
    #)
    fig_barplot = Figure(figsize=(8, max(6, anzahl_kanten * 0.2)), dpi=100)
    ax_barplot = fig_barplot.add_subplot(111)

    ax_barplot.barh(df["Kante"], df["Auslastung"], height=0.6) # Horizontale Ausrichtung der Balken | Alternativ bar() für vertikal
    ax_barplot.set_xlabel("Auslastung in %")
    ax_barplot.set_ylabel("Kante")
    ax_barplot.set_title("Kantenbelastung (%)")
    ax_barplot.invert_yaxis() # Größte Aulastung oben - Top-Down

    fig_barplot.tight_layout() # Automatische Abstände

    
    canvas_fig = FigureCanvasTkAgg(fig_barplot, master=container) # Diagramm mit Container verbinden
    canvas_fig.draw() # Diagramm zeichnen
    canvas_fig.get_tk_widget().pack(fill="both", expand=True)

    
    container.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))




#Methode erstellt ein Balkendiagramm zum Darstellen der prozentualen Auslastungen der Kanten
def zeigeKantenbelastungDiagramm():
    global simulationsAusgeführt

    if not simulationsAusgeführt:
        messagebox.showwarning("Simulation nicht ausgeführt", 
                               "Führen Sie vorher einmal die Simulation aus, um sich die prozentuale Kantenbelastung anzeigen zu lassen.")
        return

    height: list[float] = [] 
    bars: list[str] = []

    # --- 1. DATEN SAMMELN ---
    for u, v, _, attr in MG.edges(keys=True, data=True):
        kapazitätsgrenze = attr.get("Kapazitätsgrenze", 1) # Fallback 1 um Division durch 0 zu vermeiden
        restkapazität = attr.get("Restkapazität", 0)
        verbindungsart = attr.get("Verbindungsart")
        auslastung = kapazitätsgrenze - restkapazität
        auslastungProzent = (auslastung * 100) / kapazitätsgrenze
        auslastungProzent = round(auslastungProzent, 2)

        height.append(auslastungProzent)
        #bars.append(f"{u} - {v}")
        bars.append(f"({verbindungsart}) {u} - {v}")

    # --- 2. DATEN SORTIEREN (Pandas) ---
    df = pd.DataFrame({
        'Kante': bars,
        'Auslastung': height
    })
    
    # Sortieren: kleinste Auslastung zuerst (unten im Plot), größte zuletzt (oben im Plot)
    df = df.sort_values(by='Auslastung', ascending=True).reset_index(drop=True)
    anzahl_kanten = len(df)

    # --- 3. GUI SETUP (Toplevel & Scrollbar) ---
    fenster = tk.Toplevel(root)
    fenster.title("Prozentuale Belastung jeder Kante")
    fenster.geometry("1300x1000")

    canvas = tk.Canvas(fenster)
    scrollbar = tk.Scrollbar(fenster, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    container = tk.Frame(canvas)
    canvas.create_window((0, 0), window=container, anchor="nw")

    # --- 4. DIAGRAMM ERSTELLEN ---
    # Dynamische Höhe berechnen
    #fig_h = max(8, max(6, anzahl_kanten * 0.2)) 
    fig_barplot = Figure(figsize=(8, max(6, anzahl_kanten * 0.2)))
    ax_barplot = fig_barplot.add_subplot(111)

    # Index-basierter Plot für perfekte Sortierung
    y_pos = range(len(df))
    
    # Farbauswahl: Rot für Engpässe (== 100%), sonst Skyblue
    colors = ['red' if x == 100 else 'skyblue' for x in df["Auslastung"]]

    ax_barplot.barh(y_pos, df["Auslastung"], height=0.7, color=colors, edgecolor='black', alpha=0.8)

    # Achsen-Beschriftungen fixieren
    ax_barplot.set_yticks(y_pos)
    ax_barplot.set_yticklabels(df["Kante"], fontsize=9)
    
    # Optik & Orientierung
    ax_barplot.set_xlabel("Auslastung in %", fontweight='bold')
    ax_barplot.set_ylabel("Kante", fontweight='bold')
    ax_barplot.set_title("Detaillierte Kantenbelastung", pad=15, fontsize=14, fontweight='bold')
    
    # Kritische 100% Linie einzeichnen
    ax_barplot.axvline(100, color='red', linestyle='--', linewidth=2, label="Kapazitätsgrenze")
    
    # Gitternetz für bessere Lesbarkeit
    ax_barplot.grid(axis='x', linestyle=':', alpha=0.6)
    
    # Größte Auslastung nach oben
    ax_barplot.invert_yaxis() 

    fig_barplot.tight_layout()

    # --- 5. EINBETTUNG IN TKINTER ---
    canvas_fig = FigureCanvasTkAgg(fig_barplot, master=container)
    canvas_fig.draw()
    canvas_fig.get_tk_widget().pack(fill="both", expand=True)

    # Scrollregion aktualisieren
    container.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

    # Mausrad-Support (optional, aber sehr hilfreich)
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)






#Methode erstellt ein Balkendiagramm zum Darstellen wie viel Angebot durch Transitknoten fließen.
# dictTransitknotenUndAngebot: dict[str, int] = {}
def zeigeTransitknotenDiagramm():
    global simulationsAusgeführt
    global dictTransitknotenUndAngebot
    #print(dictTransitknotenUndAngebot)

    if not simulationsAusgeführt:
        messagebox.showwarning("Simulation nicht ausgeführt", 
                               "Führen Sie vorher einmal die Simulation aus, um sich die prozentuale Kantenbelastung anzeigen zu lassen.")
        return

    height: list[float] = [] 
    bars: list[str] = []

    # --- 1. DATEN SAMMELN ---
    for knoten, angebotÜbertragen in dictTransitknotenUndAngebot.items():
        height.append(angebotÜbertragen)
        bars.append(f"{knoten}")

    df = pd.DataFrame({
        'Knoten': bars,
        'Durchgelaufenes Angebot': height
    })
    df = df.sort_values(by=['Durchgelaufenes Angebot'], ascending=True)
    anzahl_kanten = len(df)


    fensterTransKnoten = tk.Toplevel(root)
    fensterTransKnoten.title("Durchlaufene Angebote pro Transitknoten")
    fensterTransKnoten.geometry("1300x1000") # Größenangabe: X-Achse x y-Achse

    
    canvasTransKnoten = tk.Canvas(fensterTransKnoten) # Erzeugt Zeichenbereich, weil Tkinter Frames nicht scrollen kann.
    scrollbarTransKnoten = tk.Scrollbar(fensterTransKnoten, orient="vertical", command=canvasTransKnoten.yview) #Erzeugung von Scrollbar und Festlegung der Scrollrichtung
    canvasTransKnoten.configure(yscrollcommand=scrollbarTransKnoten.set) # Verbdinung von Canvas-Zeichenbereich und Scrollbar.

    scrollbarTransKnoten.pack(side="right", fill="y") # Positionierung der Scrollbar und vertikale Füllung der Bar des Fensters.
    canvasTransKnoten.pack(side="left", fill="both", expand=True)

    containerTransKnoten = tk.Frame(canvasTransKnoten) # Ersetellen von Container in Zeichenbereich, in welchem Diagramm kommmen soll.
    canvasTransKnoten.create_window((0, 0), window=containerTransKnoten, anchor="nw") # Positionieren des Containers im Zeichenbereich Canvas.

    
    #fig_barplot, ax_barplot = plt.subplots(
     #   figsize=(8, max(6, anzahl_kanten * 0.4)) # Erstellen von Diagramm und Größe
    #)
    fig_transknoten = Figure(figsize=(8, max(6, anzahl_kanten * 0.2)), dpi=100)
    ax_transknoten = fig_transknoten.add_subplot(111)

    ax_transknoten.barh(df["Knoten"], df["Durchgelaufenes Angebot"], height=0.6) # Horizontale Ausrichtung der Balken | Alternativ bar() für vertikal
    ax_transknoten.set_xlabel("Durchgelaufenes Angebot")
    ax_transknoten.set_ylabel("Knoten")
    ax_transknoten.set_title("Durchlaufene Angebote pro Transitknoten")
    ax_transknoten.invert_yaxis() # Größte Aulastung oben - Top-Down

    fig_transknoten.tight_layout() # Automatische Abstände

    
    canvas_fig = FigureCanvasTkAgg(fig_transknoten, master=containerTransKnoten) # Diagramm mit Container verbinden
    canvas_fig.draw() # Diagramm zeichnen
    canvas_fig.get_tk_widget().pack(fill="both", expand=True)

    
    containerTransKnoten.update_idletasks()
    canvasTransKnoten.config(scrollregion=canvasTransKnoten.bbox("all"))





def zeigeTransportanteilProVerbindungsart():
    global simulationsAusgeführt
    global dictTransportmengeProVerbindungsart
    #print(dictTransportmengeProVerbindungsart)

    if not simulationsAusgeführt:
        messagebox.showwarning("Simulation nicht ausgeführt", 
                               "Führen Sie vorher einmal die Simulation aus, um sich die prozentuale Kantenbelastung anzeigen zu lassen.")
        return

    height_absolut: list[float] = []
    height_relativ: list[float] = [] 
    bars: list[str] = []
    übertragenesAngebotGesamt: int = sum(dictTransportmengeProVerbindungsart.values())

    # --- 1. DATEN SAMMELN ---
    for verbindungsart, angebotÜbertragen in dictTransportmengeProVerbindungsart.items():
        height_absolut.append(angebotÜbertragen)
        height_relativ.append((angebotÜbertragen*100)/übertragenesAngebotGesamt)
        bars.append(f"{verbindungsart}")


    df = pd.DataFrame({
        'Verbindungsart': bars,
        'Transportanteil': height_relativ
    })
    df = df.sort_values(by=['Transportanteil'], ascending=True)
    anzahl_kanten = len(df)


    fensterVerbindungsart = tk.Toplevel(root)
    fensterVerbindungsart.title("Transportanteil pro Verbindungsart")
    fensterVerbindungsart.geometry("1300x1000") # Größenangabe: X-Achse x y-Achse

    
    canvasVerbindungsart = tk.Canvas(fensterVerbindungsart) # Erzeugt Zeichenbereich, weil Tkinter Frames nicht scrollen kann.
    scrollbarVerbindungsart = tk.Scrollbar(fensterVerbindungsart, orient="vertical", command=canvasVerbindungsart.yview) #Erzeugung von Scrollbar und Festlegung der Scrollrichtung
    canvasVerbindungsart.configure(yscrollcommand=scrollbarVerbindungsart.set) # Verbdinung von Canvas-Zeichenbereich und Scrollbar.

    scrollbarVerbindungsart.pack(side="right", fill="y") # Positionierung der Scrollbar und vertikale Füllung der Bar des Fensters.
    canvasVerbindungsart.pack(side="left", fill="both", expand=True)

    containerverbindungsart = tk.Frame(canvasVerbindungsart) # Ersetellen von Container in Zeichenbereich, in welchem Diagramm kommmen soll.
    canvasVerbindungsart.create_window((0, 0), window=containerverbindungsart, anchor="nw") # Positionieren des Containers im Zeichenbereich Canvas.

    
    #fig_barplot, ax_barplot = plt.subplots(
     #   figsize=(8, max(6, anzahl_kanten * 0.4)) # Erstellen von Diagramm und Größe
    #)
    fig_verbindungsart = Figure(figsize=(8, max(6, anzahl_kanten * 0.2)), dpi=100)
    ax_verbindungsart = fig_verbindungsart.add_subplot(111)

    ax_verbindungsart.bar(df["Verbindungsart"], df["Transportanteil"], width=0.6)
    ax_verbindungsart.set_xlabel("Verbindungsart")
    ax_verbindungsart.set_ylabel("Transportanteil (%)")
    ax_verbindungsart.set_title("Transportanteil pro Verbindungsart")
    #ax_verbindungsart.invert_yaxis() # Größte Aulastung oben - Top-Down

    fig_verbindungsart.tight_layout() # Automatische Abstände

    
    canvas_fig = FigureCanvasTkAgg(fig_verbindungsart, master=containerverbindungsart) # Diagramm mit Container verbinden
    canvas_fig.draw() # Diagramm zeichnen
    canvas_fig.get_tk_widget().pack(fill="both", expand=True)

    
    containerverbindungsart.update_idletasks()
    canvasVerbindungsart.config(scrollregion=canvasVerbindungsart.bbox("all"))



#==========================================================================================================================



def datenVorbereitenPiechartAngebotTop6() -> list[list[int], list[str]]:
    result: list[list[int], list[str]] = [] # list[daten, labels]

    global knoten_list # list[dict[str, str | int | tuple[float, float]]]

    netzwerkAngebotGesamt: int = 0
    knotenAngebotListe: list[tuple[str, int]] = []
    
    for dictionary in knoten_list:
        knoten: str = dictionary.get('Name')
        angebot: int = dictionary.get('Angebot')
        netzwerkAngebotGesamt += angebot
        knotenAngebotListe.append((knoten, angebot))

    topSechsAngeboteMitKnoten: list[tuple[str, int]] = sorted(knotenAngebotListe, key=lambda x: x[1], reverse=True)[:6] #Enthält die sechs größten Angebote zusammen mir ihren Knoten.
    topSechsKnoten: list[str] = list(map(lambda x: x[0], topSechsAngeboteMitKnoten))   #Enthält sie zugehörigen Knoten zu den sechs größten Angeboten.
    topSechsAngebote: list[int] = list(map(lambda x: x[1], topSechsAngeboteMitKnoten)) #Enthält die sechs größten Angebote


    data: list[int] = list(topSechsAngebote) # data soll eine Kopie von topSechsAngebote sein.
    labels: list[str] = []
    for knoten, angebot in zip(topSechsKnoten, topSechsAngebote):
        labels.append(f"{knoten}\n({angebot} t/Jahr)")

    data.append(netzwerkAngebotGesamt - sum(topSechsAngebote))
    labels.append(f"sonstige\n({netzwerkAngebotGesamt - sum(topSechsAngebote)} t/Jahr)")

    result.append(data)
    result.append(labels)
    #print(result)   # [[9412281, 9412281, 4433439, 4327153, 3064235, 3061431, 8827076], ['Duisburg\n(9412281 t/Jahr)', 'Duisburg Inlandhafen\n(9412281 t/Jahr)', 'Köln\n(4433439 t/Jahr)', 'Köln-Hafen\n(4327153 t/Jahr)', 'Hamburg\n(3064235 t/Jahr)', 'Hamburg-Hafen\n(3061431 t/Jahr)', 'sonstige\n(8827076 t/Jahr)']]
    return result


def datenVorbereitenVerhältnisAngebotverteilung() -> tuple[int, int]:
    result: list[int, int] = []
    sumAngebot: int = 0
    global sumAngebotVerteilt
    global knoten_list

    for dictionary in knoten_list:
        angebot: int = dictionary.get('Angebot')
        sumAngebot += angebot

    result.append(sumAngebotVerteilt)
    result.append(sumAngebot)
    return result


def zeigePieCHartZuAngeboten():
    # fig.canvas.draw_idle()
    global simulationsAusgeführt

    if simulationsAusgeführt == False:
        messagebox.showwarning("Simulations nicht ausgeführt", "Führen Sie vorher einmal die Simulation aus, um sich Angebotsinformationen anzeigen zu lassen.")
        return
    
    # Daten für Piechar_1 holen ===========================
    datenPiecharAngebot: list[list[int], list[str]] = datenVorbereitenPiechartAngebotTop6()
    data1: list[int] = datenPiecharAngebot[0]
    labels1: list[str] = datenPiecharAngebot[1]

    # Daten für Piechar_2 holen ============================
    data2_vorläufig: list[int, int] = datenVorbereitenVerhältnisAngebotverteilung() # [sumAngebotVerteilt, sumAngebot]
    data2: list[int] = []
    data2.append(data2_vorläufig[0])
    sumAngebotUnverteilt: int = data2_vorläufig[1] - data2_vorläufig[0]
    data2.append(sumAngebotUnverteilt)
    # data2 -> [sumAngebotVerteilt, sumAngebotUnverteilt]
    labels2: list[str] = ["Verteiltes Angebot", "Unverteiltes Angebot"]

    print()
    print("Summe Angebot:", data2_vorläufig[1])
    print("Angebot unverteilt:", sumAngebotUnverteilt)
    print("Angebot verteilt:", data2_vorläufig[0])
    print()

    # Fenster erzeugen ==========================
    fenster = tk.Toplevel(root)
    fenster.title("Statistiken zu Angeboten")

    hbox = tk.Frame(fenster)
    hbox.pack(fill="both", expand=True, padx=10, pady=10)

    # Piechar_1 erzeugen und mit Daten füllen ===========================
    #fig_pie1, ax_pie1 = plt.subplots()
    fig_pie1 = Figure(figsize=(6, 5), dpi=100)
    ax_pie1 = fig_pie1.add_subplot(111)

    #ax_piechar1.pie(data1, labels=labels1, autopct="%1.1f%%")
    #ax_piechar1.set_title("Top sechs Angebote (absolut & relativ)\nvor Angebotsverteilung", pad=10, fontsize=14, fontweight='bold')
    
    ax_pie1.pie(data1, labels=labels1, autopct="%1.1f%%")
    ax_pie1.set_title("Top sechs Angebote (absolut & relativ)\nnach Knoten vor Angebotsverteilung", pad=10, fontsize=14, fontweight='bold')

    #canvas_1 = FigureCanvasTkAgg(fig_piechar1, master=hbox)
    canvas_1 = FigureCanvasTkAgg(fig_pie1, master=hbox)
    #canvas_1.get_tk_widget().pack()
    canvas_1.get_tk_widget().pack(side="left", fill="both", expand=True)
    canvas_1.draw()


    separator = ttk.Separator(hbox, orient="vertical")
    separator.pack(side="left", fill="y", padx=15)


    #Piechar_2 erzeugen und mit Date füllen ===========================    
    #fig_pie2, ax_pie2 = plt.subplots()
    fig_pie2 = Figure(figsize=(6, 5), dpi=100)
    ax_pie2 = fig_pie2.add_subplot(111)

    #ax_pie2.pie(data2, labels=labels2, autopct="%1.1f%%")
    #ax_pie2.set_title("Verhältnis Ist- und Soll-Angebotsverteilung", pad=10, fontsize=14, fontweight='bold')
    ax_pie2.pie(data2, labels=labels2, autopct="%1.1f%%")
    ax_pie2.set_title("Verhältnis Ist- und Soll-Angebotsverteilung", pad=10, fontsize=14, fontweight='bold')

    #canvas_2 = FigureCanvasTkAgg(fig_pie2, master=hbox)
    canvas_2 = FigureCanvasTkAgg(fig_pie2, master=hbox)
    #canvas_2.get_tk_widget().pack()
    canvas_2.get_tk_widget().pack(side="left", fill="both", expand=True)
    canvas_2.draw()

"""
    % -> Startzeichen für Formatierung
    1 -> Mindestbreite des Textes
    .1 -> Anzahl Nachkommastellen
    f -> Zahl als Fließkommazahl darstellen
    %% -> Anzeigen von Prozentzeichen
"""
#-------------------------------------------------------------------------------------------------------------------------------------------->




#<-------------------------------------------------------------------------------------------------------------------------------------------<
# Canvas in Tkinter
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Toolbar
toolbar = NavigationToolbar2Tk(canvas, root) #Erstellt Matplotlib-Toolbar für Karte/Zeichenbereich (mit Zoom, Speichern, etc.)
toolbar.update()
toolbar.pack(fill=tk.X) #Matplotlib-Toolbar unten im Fenster positionieren und füllt sie horizontal aus.

root.mainloop() #Jetzt reagiert das Fenster auf Benutzerinteraktionen.
#Führt initial und implizit das Zeichnen aus. Also canvas.draw() oder plt.show()
#Darum braucht man in den Methoden "zeichne_icon_an_knotenposition", "zeicne_knotenlabels" und "zeichne_kanten" kein "fig.canvas.draw_idle()".
#Aber, wenn nach Programmstart der Plot nochmal neu gezeichnet werden muss, muss man explizit "fig.canvas.draw_idle()" aufrufen.


#---------------------------------------------------------------------------------------------------------------------------------------------->