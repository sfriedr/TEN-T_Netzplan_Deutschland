# TEN-T Netzsimulation Fokus Deutschland
Eine Python-Anwendung zur Erstellung eines Graphenmodells des Transeuropäischen Transportnetzes (TEN-T) nach Verordnung (EU) 2024/1679 mit Fokus auf Deutschland sowie Simulation der Angebotsveerteilung der Knoten und späterer Analyse.
![Benutzeroberfläche der Anwendung](/docs/screenshots/GUI.png "GUI")

Auf diesem Graphenmodell werden Städte, Häfen und Flughäfen als Knoten modelliert und entsprechende Verbindungen über Straße, Wasser, Schiene und Luft als Kanten. Durch die Integration externer Informationen, wie wirtschaftlicher Kennzahlen oder Kapazitätsannahmen, soll das Modell um realitätsnahe Einflussfaktoren erweitert werden. Auf Basis dieses Modells wird simuliert, wie einzelne Knoten ihre Angebote in t/Jahr an andere Knoten verteilen.
Dabei werden zentrale Fragestellungen des Supply Chain Managements adressieren. Das inkludiert die Identifikation von Zielknoten als Empfänger von Angeboten, die Analyse von Engpässen und Störungen einzelner Verbindungen durch gezieltes Entfernen von Kanten, wichtige Transitknoten des Netzes, das Aufweisen der Belastungen einzelner Kanten. Des weiteren werden die Transportanteile der Verbindungsarten (Straße, Schiene, Luft, Wasser) ersichtlich sowie die größten Anbieter im Netz. Diese Informationen können über das Menü bezogen werden.

## Hier ein paar Beispiele, welche Analysen durch das Menü nach der Simulation durchefühert werden können:
![Engpässe auf Straße, Schiene, Wasser, Luft](/docs/screenshots/Engpässe.png "Kantenengpässe")
![Detailansicht der Kantenauslastungen](/docs/screenshots/Detaillierte_Kantenbelastungen.png "Engpässe Detailansicht")
![Angebotsverteilung](/docs/screenshots/Angebotsverteilung.png "Angebotsverteilung")

## Technische Implementierung und Bibliotheken
Anbindung einer MySQL-Datenbank, welche Knoten- und Kantenattribute enthält.
Die wichtigsten Python-Bibliotheken:
* networkx: Zur Erzeugung eines Multigraphen, welches das TEN-T Netz darstellt.
* cartopy: Zur Erzeugung der Deutschlandkarte
* matplotlib: Zur Visualisierung von Diagrammen (Piechart, Barchart)

## Umfang und Informationsbeschaffung
Aus den insgesamt 158 Knoten aus Anhang II, S. 126 ff. Verordnung (EU) 2024/1679 wurden 36 ausgewählt. Zwischen diese Knoten bestehen ingesamt 81 Verbindungen. Darstellung und Bedeutung der Knoten und Kanten orientiert sich an der aus Verordnung Anhang I, S. 76. Nur die Darstellung des Engpasses ist eine eigene Interpretation. Die TEN-T Knoten wurden aus Anhang II, S. 126 ff. Verordnung (EU) 2024/1679 ausgewählt. Sämtliche weitere externe Informationen bezüglich der Knoten wie bspw. BIP, Bevölkerungszahl, Anzahl Güterzüge, Anzahl Starts und Landungen pro Flughafen etc. wurden hauptsächlich den statistischen Ämtern des Bundes und der Länder entnommen.

## Kritische Anmerkung
Das Modell bietet keine 100%ige Repräsentativität. Das sieht man, weil z.B. meist nur 1/5 des Angebots vollständig verteilt wird oder dass die Straße nicht auf Platz 1 beim Gütertransport ist. Grund dafür ist, dass die Anwendung nur einen Bruchteil des tatsächlichen Netzes darstellt. Dementsprechend können bei Engpässen Kanten bzw. Ausweichrouten nicht in Betracht genommen werden, die in dem Modell nicht existieren. Darüberhinaus ist die Datengrundlage bzw. -verfügbarkeit teils mangelhaft. Darum mussten manche Daten geschätzt werden. Dennoch zeigt das Modell realistische Auslastung, welche des Netzes, welche im Westen am größten ist oder auch die strategisch wichtigsten Knoten. Letzen Endes ist es keine wissenschaftliche Studie, sondern eine interessante Möglichkeit zu testen, was technisch in Python möglich ist.