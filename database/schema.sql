CREATE TABLE Knoten (
    Name VARCHAR(20),
    Längengrad DECIMAL (8,6) UNSIGNED,
    Breitengrad DECIMAL (8,6) UNSIGNED,
    Typ ENUM('Stadt', 'Hafen', 'Flughafen'),
    Kapazität INTEGER UNSIGNED,
    Auslastung INTEGER UNSIGNED,
    Angebot INTEGER UNSIGNED,
    CHECK (Kapazität >= Auslastung),
    CHECK (Auslastung >= Angebot),
    PRIMARY KEY (Name, Typ),
    UNIQUE KEY uk_coords (Längengrad, Breitengrad)
);

CREATE TABLE Stadtknoten (
    Name VARCHAR(20),
    Längengrad DECIMAL (8,6) UNSIGNED,
    Breitengrad DECIMAL (8,6) UNSIGNED,
    Kapazität INTEGER UNSIGNED,
    Auslastung INTEGER UNSIGNED,
    Angebot INTEGER UNSIGNED,
    BIP INTEGER,
    Bevölkerungszahl INTEGER UNSIGNED,
    CHECK (Kapazität >= Auslastung),
    CHECK (Auslastung >= Angebot),
    PRIMARY KEY (Name, Längengrad, Breitengrad)
    );

CREATE TABLE Hafenknoten (
    Name VARCHAR(20),
    Längengrad DECIMAL (8,6) UNSIGNED,
    Breitengrad DECIMAL (8,6) UNSIGNED,
    Kapazität INTEGER UNSIGNED,
    Auslastung INTEGER UNSIGNED,
    Angebot INTEGER UNSIGNED,
    CHECK (Kapazität >= Auslastung),
    CHECK (Auslastung >= Angebot),
    PRIMARY KEY (Name, Längengrad, Breitengrad)
    );

CREATE TABLE Flughafenknoten (
    Name VARCHAR(20),
    Längengrad DECIMAL (8,6) UNSIGNED,
    Breitengrad DECIMAL (8,6) UNSIGNED,
    Kapazität INTEGER UNSIGNED,
    Auslastung INTEGER UNSIGNED,
    Angebot INTEGER UNSIGNED,
    Anzahl_Start INTEGER UNSIGNED,
    Anzahl_Landung INTEGER UNSIGNED,
    CHECK (Kapazität >= Auslastung),
    CHECK (Auslastung >= Angebot),
    PRIMARY KEY (Name, Längengrad, Breitengrad)
    );

CREATE TABLE Kante (
    Startknoten_Name VARCHAR(20),
    Startknoten_Längengrad DECIMAL(8,6) UNSIGNED,
    Startknoten_Breitengrad DECIMAL(8,6) UNSIGNED,
    Endknoten_Name VARCHAR(20),
    Endknoten_Längengrad DECIMAL(8,6) UNSIGNED,
    Endknoten_Breitengrad DECIMAL(8,6) UNSIGNED,
    Verbindungsart ENUM('Straße', 'Schiene', 'Wasser', 'Luft'),
    Kapazitätsgrenze INTEGER UNSIGNED,
    Restkapazität INTEGER UNSIGNED,
    Engpass TINYINT(1) GENERATED ALWAYS AS (Restkapazität = 0) STORED,
    PRIMARY KEY (Startknoten_Name, Endknoten_Name, Verbindungsart),
    FOREIGN KEY (Startknoten_Längengrad, Startknoten_Breitengrad)
        REFERENCES knoten(Längengrad, Breitengrad)
        ON DELETE CASCADE,
    FOREIGN KEY (Endknoten_Längengrad, Endknoten_Breitengrad)
        REFERENCES knoten(Längengrad, Breitengrad)
        ON DELETE CASCADE
    );


/* Trigger Stadtknoten_in_Knoten_einfügen*/
DELIMITER $$

CREATE TRIGGER Stadtknoten_in_Knoten_einfügen
AFTER INSERT ON Stadtknoten
FOR EACH ROW
BEGIN
    INSERT INTO Knoten (
        Name, Längengrad, Breitengrad, Typ, Kapazität, Auslastung, Angebot
    )
    VALUES (
        NEW.Name, NEW.Längengrad, NEW.Breitengrad, 'Stadt',
        NEW.Kapazität, NEW.Auslastung, NEW.Angebot
    );
END$$

DELIMITER ;


/* Trigger Stadtknoten_aus_Knoten_löschen*/
DELIMITER $$

CREATE TRIGGER Stadtknoten_aus_Knoten_löschen
AFTER DELETE ON Stadtknoten
FOR EACH ROW
BEGIN
    DELETE FROM Knoten
    WHERE Name = OLD.Name AND Typ = 'Stadt';
END$$

DELIMITER ;


/* Trigger Hafenknoten_in_Knoten_einfügen*/
DELIMITER $$

CREATE TRIGGER Hafenknoten_in_Knoten_einfügen
AFTER INSERT ON Hafenknoten
FOR EACH ROW
BEGIN
    INSERT INTO Knoten (
        Name, Längengrad, Breitengrad, Typ, Kapazität, Auslastung, Angebot
    )
    VALUES (
        NEW.Name, NEW.Längengrad, NEW.Breitengrad, 'Hafen',
        NEW.Kapazität, NEW.Auslastung, NEW.Angebot
    );
END$$

DELIMITER ;



/* Trigger Hafenknoten_in_Knoten_einfügen*/
DELIMITER $$

CREATE TRIGGER Hafenknoten_aus_Knoten_löschen
AFTER DELETE ON Hafenknoten
FOR EACH ROW
BEGIN
    DELETE FROM Knoten
    WHERE Name = OLD.Name AND Typ = 'Hafen';
END$$

DELIMITER ;



/* Trigger Hafenknoten_in_Knoten_einfügen*/
DELIMITER $$

CREATE TRIGGER Flughafenknoten_in_Knoten_einfügen
AFTER INSERT ON Flughafenknoten
FOR EACH ROW
BEGIN
    INSERT INTO Knoten (
        Name, Längengrad, Breitengrad, Typ, Kapazität, Auslastung, Angebot
    )
    VALUES (
        NEW.Name, NEW.Längengrad, NEW.Breitengrad, 'Flughafen',
        NEW.Kapazität, NEW.Auslastung, NEW.Angebot
    );
END$$

DELIMITER ;



/* Trigger Hafenknoten_in_Knoten_einfügen*/
DELIMITER //

CREATE TRIGGER Flughafenknoten_aus_Knoten_löschen
AFTER DELETE ON Flughafenknoten
FOR EACH ROW
BEGIN
    DELETE FROM Knoten 
    -- Hier wichtig: 'Flughafen' in Anführungszeichen!
    WHERE Name = OLD.Name AND Typ = 'Flughafen';
END //

DELIMITER ;




INSERT INTO Stadtknoten
(Name, Längengrad, Breitengrad, Kapazität, Auslastung, Angebot, BIP, Bevölkerungszahl)
VALUES
('Berlin', 13.405000, 52.520000, 1378716, 1084651, 294065, 197924, 3685265),
('Duisburg', 6.762000, 51.434400, 41644572, 32232291, 9412281, 20218, 0),
('Düsseldorf', 6.773510, 51.227700, 979153, 669594, 309559, 63274, 618685),
('Frankfurt a. M.', 8.636580, 50.121250, 2665709, 442196, 442195, 89341, 756021),
('Hamburg', 9.993700, 53.551100, 6597385, 3533150, 3064235, 153737, 1851596),
('Hannover', 9.732000, 52.375900, 613880, 307142, 306738, 65277, 558051),
('Koblenz', 7.588900, 50.356900, 825201, 525517, 299684, 10130, 113376),
('Köln', 6.960300, 50.937500, 9018886, 4433440, 4433439, 79385, 1024621),
('Leipzig', 12.373100, 51.339700, 347083, 168233, 168232, 29013, 611850),
('Magdeburg', 11.627600, 52.120500, 2691351, 1151774, 1151773, 10363, 244329),
('München', 11.582000, 48.135100, 8867, 3210, 3209, 147233, 1505005),
('Regensburg', 12.101600, 49.013900, 941585, 570583, 371002, 16063, 151389),
('Stuttgart', 9.182900, 48.775800, 569135, 341272, 227863, 71032, 612986),
('Nürnberg', 11.076700, 49.452100, 7949, 4051, 3898, 38157, 529508),
('Rostock', 12.099100, 54.092400, 160412, 110231, 50181, 10374, 205307);




INSERT INTO Hafenknoten
(Name, Längengrad, Breitengrad, Kapazität, Auslastung, Angebot)
VALUES
('Berlin-Westhafen', 13.290000, 52.534000, 1369849, 1081441, 288408),
('Braunschweig-Hafen', 10.481860, 52.314230, 704154, 405087, 299067),
('Duisburg Inlandhafen', 6.747500, 51.445500, 41644572, 32232291, 9412281),
('Düsseldorf-Hafen', 6.757800, 51.219000, 973257, 667478, 305779),
('Hamburg-Hafen', 9.969000, 53.546700, 6593244, 3531813, 3061431),
('Hannover-Hafen', 9.691300, 52.371400, 613880, 307142, 306738),
('Koblenz-Hafen', 7.593000, 50.393000, 825201, 525517, 299684),
('Köln-Hafen', 6.983300, 50.940000, 8797089, 4327154, 4327153),
('Magdeburg-Hafen', 11.648000, 52.125000, 2691351, 1151774, 1151773),
('Mainz-Hafen', 8.656420, 50.106840, 3222384, 1999512, 1222872),
('Frankfurt-Hafen', 8.266667, 50.000000, 2220309, 232924, 232923),
('Regensburg-Hafen', 12.106900, 49.009100, 941585, 570583, 371002),
('Stuttgart-Hafen', 9.254500, 48.767700, 561091, 337794, 223297);




INSERT INTO Flughafenknoten
(Name, Längengrad, Breitengrad, Kapazität, Auslastung, Angebot, Anzahl_Start, Anzahl_Landung)
VALUES
('BER', 13.500600, 52.362200, 8867, 3210, 3209, 16629, 16789),
('DUS', 6.766700, 51.289400, 5896, 2116, 2115, 13257, 13322),
('FRA', 8.573300, 50.041100, 445400, 209272, 209271, 43744, 43629),
('HAM', 9.988100, 53.630300, 4141, 1337, 1336, 9875, 9972),
('CGN', 7.142800, 50.865000, 221797, 106286, 106285, 10242, 10328),
('LEJ', 12.220300, 51.421900, 347083, 168233, 168232, 8569, 8518),
('MUC', 11.781700, 48.353900, 8867, 3210, 3209, 30191, 30135),
('STR', 9.210000, 48.688100, 8044, 3478, 3477, 6714, 6684);




INSERT INTO Kante
(Startknoten_Name, Startknoten_Längengrad, Startknoten_Breitengrad,
 Endknoten_Name, Endknoten_Längengrad, Endknoten_Breitengrad,
 Verbindungsart, Kapazitätsgrenze, Restkapazität)
VALUES
('Berlin', 13.405000, 52.520000, 'Rostock', 12.099100, 54.092400, 'Straße', 10378572, 10378572),
('Berlin', 13.405000, 52.520000, 'Leipzig', 12.373100, 51.339700, 'Straße', 36910056, 36910056),
('Berlin', 13.405000, 52.520000, 'Magdeburg', 11.627600, 52.120500, 'Straße', 61040358, 61040358),
('Magdeburg', 11.627600, 52.120500, 'Hannover', 9.732000, 52.375900, 'Straße', 78247254, 78247254),
('Hannover', 9.732000, 52.375900, 'Hamburg', 9.993700, 53.551100, 'Straße', 44809778, 44809778),
('Hannover', 9.732000, 52.375900, 'Duisburg', 6.762000, 51.434400, 'Straße', 178051745, 178051745),
('Duisburg', 6.762000, 51.434400, 'Düsseldorf', 6.757800, 51.219000, 'Straße', 192534619, 192534619),
('Düsseldorf', 6.757800, 51.219000, 'Köln', 6.960300, 50.937500, 'Straße', 171785349, 171785349),
('Köln', 6.960300, 50.937500, 'Koblenz', 7.588900, 50.356900, 'Straße', 186768924, 186768924),
('Koblenz', 7.588900, 50.356900, 'Frankfurt a. M.', 8.636580, 50.121250, 'Straße', 21120678, 21120678),
('Frankfurt a. M.', 8.636580, 50.121250, 'Stuttgart', 9.182900, 48.775800, 'Straße', 46028480, 46028480),
('Stuttgart', 9.182900, 48.775800, 'München', 11.582000, 48.135100, 'Straße', 37306567, 37306567),
('Frankfurt a. M.', 8.636580, 50.121250, 'Nürnberg', 11.076700, 49.452100, 'Straße', 44492814, 44492814),
('Nürnberg', 11.076700, 49.452100, 'Regensburg', 12.101600, 49.013900, 'Straße', 32579871, 32579871),
('Nürnberg', 11.076700, 49.452100, 'München', 11.582000, 48.135100, 'Straße', 36434099, 36434099),
('Nürnberg', 11.076700, 49.452100, 'Leipzig', 12.373100, 51.339700, 'Straße', 32898478, 32898478);




INSERT INTO Kante
(Startknoten_Name, Startknoten_Längengrad, Startknoten_Breitengrad,
 Endknoten_Name, Endknoten_Längengrad, Endknoten_Breitengrad,
 Verbindungsart, Kapazitätsgrenze, Restkapazität)
VALUES
('Berlin', 13.405000, 52.520000, 'Berlin-Westhafen', 13.290000, 52.534000, 'Straße', 17000000, 17000000),
('Berlin', 13.405000, 52.520000, 'BER', 13.500600, 52.362200, 'Straße', 13000000, 13000000),
('Magdeburg', 11.627600, 52.120500, 'Magdeburg-Hafen', 11.648000, 52.125000, 'Straße', 10000000, 10000000),
('Hamburg', 9.993700, 53.551100, 'Hamburg-Hafen', 9.969000, 53.546700, 'Straße', 12000000, 12000000),
('Hamburg', 9.993700, 53.551100, 'HAM', 9.988100, 53.630300, 'Straße', 10000000, 10000000),
('Hannover', 9.732000, 52.375900, 'Hannover-Hafen', 9.691300, 52.371400, 'Straße', 17000000, 17000000),
('Duisburg', 6.762000, 51.434400, 'Duisburg Inlandhafen', 6.747500, 51.445500, 'Straße', 16000000, 16000000),
('Düsseldorf', 6.757800, 51.219000, 'Düsseldorf-Hafen', 6.757800, 51.219000, 'Straße', 13000000, 13000000),
('Düsseldorf', 6.757800, 51.219000, 'DUS', 6.766700, 51.289400, 'Straße', 17000000, 17000000),
('Köln', 6.960300, 50.937500, 'Köln-Hafen', 6.983300, 50.940000, 'Straße', 12500000, 12500000),
('Köln', 6.960300, 50.937500, 'CGN', 7.142800, 50.865000, 'Straße', 13500000, 13500000),
('Koblenz', 7.588900, 50.356900, 'Koblenz-Hafen', 7.593000, 50.393000, 'Straße', 12000000, 12000000),
('Leipzig', 12.373100, 51.339700, 'LEJ', 12.220300, 51.421900, 'Straße', 10500000, 10500000),
('Frankfurt a. M.', 8.636580, 50.121250, 'Frankfurt-Hafen', 8.266667, 50.000000, 'Straße', 13500000, 13500000),
('Frankfurt a. M.', 8.636580, 50.121250, 'FRA', 8.573300, 50.041100, 'Straße', 11000000, 11000000),
('Stuttgart', 9.182900, 48.775800, 'Stuttgart-Hafen', 9.254500, 48.767700, 'Straße', 12000000, 12000000),
('Stuttgart', 9.182900, 48.775800, 'STR', 9.210000, 48.688100, 'Straße', 9000000, 9000000),
('München', 11.582000, 48.135100, 'MUC', 11.781700, 48.353900, 'Straße', 7000000, 7000000),
('Regensburg', 12.101600, 49.013900, 'Regensburg-Hafen', 12.106900, 49.009100, 'Straße', 6500000, 6500000);




INSERT INTO Kante
(Startknoten_Name, Startknoten_Längengrad, Startknoten_Breitengrad,
 Endknoten_Name, Endknoten_Längengrad, Endknoten_Breitengrad,
 Verbindungsart, Kapazitätsgrenze, Restkapazität)
VALUES
('Berlin', 13.405000, 52.520000, 'Rostock', 12.099100, 54.092400, 'Schiene', 11103300, 11103300),
('Berlin', 13.405000, 52.520000, 'Leipzig', 12.373100, 51.339700, 'Schiene', 14804400, 14804400),
('Berlin', 13.405000, 52.520000, 'Magdeburg', 11.627600, 52.120500, 'Schiene', 16654950, 16654950),
('Magdeburg', 11.627600, 52.120500, 'Hannover', 9.732000, 52.375900, 'Schiene', 46263750, 46263750),
('Hannover', 9.732000, 52.375900, 'Hamburg', 9.993700, 53.551100, 'Schiene', 35160450, 35160450),
('Hannover', 9.732000, 52.375900, 'Duisburg', 6.762000, 51.434400, 'Schiene', 14804400, 14804400),
('Duisburg', 6.762000, 51.434400, 'Düsseldorf', 6.757800, 51.219000, 'Schiene', 25907700, 25907700),
('Düsseldorf', 6.757800, 51.219000, 'Köln', 6.960300, 50.937500, 'Schiene', 25907700, 25907700),
('Köln', 6.960300, 50.937500, 'Koblenz', 7.588900, 50.356900, 'Schiene', 29608800, 29608800),
('Koblenz', 7.588900, 50.356900, 'Frankfurt a. M.', 8.636580, 50.121250, 'Schiene', 25907700, 25907700),
('Frankfurt a. M.', 8.636580, 50.121250, 'Stuttgart', 9.182900, 48.775800, 'Schiene', 29608800, 29608800),
('Stuttgart', 9.182900, 48.775800, 'Nürnberg', 11.076700, 49.452100, 'Schiene', 11103300, 11103300),
('Frankfurt a. M.', 8.636580, 50.121250, 'Nürnberg', 11.076700, 49.452100, 'Schiene', 42562650, 42562650),
('Nürnberg', 11.076700, 49.452100, 'Regensburg', 12.101600, 49.013900, 'Schiene', 55516500, 55516500),
('Nürnberg', 11.076700, 49.452100, 'München', 11.582000, 48.135100, 'Schiene', 12015900, 12015900),
('Nürnberg', 11.076700, 49.452100, 'Leipzig', 12.373100, 51.339700, 'Schiene', 9252750, 9252750);




INSERT INTO Kante
(Startknoten_Name, Startknoten_Längengrad, Startknoten_Breitengrad,
 Endknoten_Name, Endknoten_Längengrad, Endknoten_Breitengrad,
 Verbindungsart, Kapazitätsgrenze, Restkapazität)
VALUES
('Berlin-Westhafen', 13.290000, 52.534000, 'Magdeburg-Hafen', 11.648000, 52.125000, 'Wasser', 2500000, 2500000),
('Magdeburg-Hafen', 11.648000, 52.125000, 'Braunschweig-Hafen', 10.481860, 52.314230, 'Wasser', 17500000, 17500000),
('Braunschweig-Hafen', 10.481860, 52.314230, 'Hamburg-Hafen', 9.969000, 53.546700, 'Wasser', 14500000, 14500000),
('Braunschweig-Hafen', 10.481860, 52.314230, 'Hannover-Hafen', 9.691300, 52.371400, 'Wasser', 17500000, 17500000),
('Hannover-Hafen', 9.691300, 52.371400, 'Duisburg Inlandhafen', 6.747500, 51.445500, 'Wasser', 17500000, 17500000),
('Duisburg Inlandhafen', 6.747500, 51.445500, 'Düsseldorf-Hafen', 6.757800, 51.219000, 'Wasser', 144500000, 144500000),
('Düsseldorf-Hafen', 6.757800, 51.219000, 'Köln-Hafen', 6.983300, 50.940000, 'Wasser', 144500000, 144500000),
('Köln-Hafen', 6.983300, 50.940000, 'Koblenz-Hafen', 7.593000, 50.393000, 'Wasser', 144500000, 144500000),
('Koblenz-Hafen', 7.593000, 50.393000, 'Mainz-Hafen', 8.656420, 50.106840, 'Wasser', 144500000, 144500000),
('Mainz-Hafen', 8.656420, 50.106840, 'Stuttgart-Hafen', 9.254500, 48.767700, 'Wasser', 144500000, 144500000),
('Mainz-Hafen', 8.656420, 50.106840, 'Frankfurt-Hafen', 8.266667, 50.000000, 'Wasser', 15500000, 15500000),
('Frankfurt-Hafen', 8.266667, 50.000000, 'Regensburg-Hafen', 12.106900, 49.009100, 'Wasser', 15500000, 15500000);




INSERT INTO Kante
(Startknoten_Name, Startknoten_Längengrad, Startknoten_Breitengrad,
 Endknoten_Name, Endknoten_Längengrad, Endknoten_Breitengrad,
 Verbindungsart, Kapazitätsgrenze, Restkapazität)
VALUES
('BER', 13.500600, 52.362200, 'FRA', 8.573300, 50.041100, 'Luft', 192, 192),
('BER', 13.500600, 52.362200, 'CGN', 7.142800, 50.865000, 'Luft', 6108, 6108),
('BER', 13.500600, 52.362200, 'MUC', 11.781700, 48.353900, 'Luft', 6084, 6084),
('BER', 13.500600, 52.362200, 'STR', 9.210000, 48.688100, 'Luft', 1836, 1836),
('DUS', 6.766700, 51.289400, 'FRA', 8.573300, 50.041100, 'Luft', 12, 12),
('DUS', 6.766700, 51.289400, 'MUC', 11.781700, 48.353900, 'Luft', 72, 72),
('FRA', 8.573300, 50.041100, 'HAM', 9.988100, 53.630300, 'Luft', 648, 648),
('FRA', 8.573300, 50.041100, 'CGN', 7.142800, 50.865000, 'Luft', 29, 29),
('FRA', 8.573300, 50.041100, 'LEJ', 12.220300, 51.421900, 'Luft', 11724, 11724),
('FRA', 8.573300, 50.041100, 'MUC', 11.781700, 48.353900, 'Luft', 1728, 1728),
('FRA', 8.573300, 50.041100, 'STR', 9.210000, 48.688100, 'Luft', 12, 12),
('HAM', 9.988100, 53.630300, 'MUC', 11.781700, 48.353900, 'Luft', 348, 348),
('CGN', 7.142800, 50.865000, 'LEJ', 12.220300, 51.421900, 'Luft', 12960, 12960),
('CGN', 7.142800, 50.865000, 'MUC', 11.781700, 48.353900, 'Luft', 8844, 8844),
('CGN', 7.142800, 50.865000, 'STR', 9.210000, 48.688100, 'Luft', 1560, 1560),
('LEJ', 12.220300, 51.421900, 'MUC', 11.781700, 48.353900, 'Luft', 6720, 6720),
('LEJ', 12.220300, 51.421900, 'STR', 9.210000, 48.688100, 'Luft', 5316, 5316),
('MUC', 11.781700, 48.353900, 'STR', 9.210000, 48.688100, 'Luft', 5316, 5316);