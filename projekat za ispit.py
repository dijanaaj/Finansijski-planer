import sys
import os
import sqlite3
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate


# KLASA: Rad sa bazom podataka
class Baza:
    def __init__(self):
        # Kreiranje putanje baze u istom folderu gde je program
        putanja_baze = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bazapodataka.db")
        # Povezivanje na SQLite bazu sa tom putanjom
        self.con = sqlite3.connect(putanja_baze)
        self.cur = self.con.cursor()

        # Kreiranje tabele 'korisnici' ako ne postoji (id, korisnicko_ime, lozinka)
        self.cur.execute("""CREATE TABLE IF NOT EXISTS korisnici (
            id INTEGER PRIMARY KEY, korisnicko_ime TEXT UNIQUE, lozinka TEXT)""")

        # Kreiranje tabele 'transakcije' ako ne postoji
        # sa poljima: id, korisnik_id (spoljni ključ), tip, kategorija, iznos, opis, datum
        self.cur.execute("""CREATE TABLE IF NOT EXISTS transakcije (
            id INTEGER PRIMARY KEY, korisnik_id INTEGER, tip TEXT,
            kategorija TEXT, iznos REAL, opis TEXT, datum TEXT DEFAULT CURRENT_DATE,
            FOREIGN KEY(korisnik_id) REFERENCES korisnici(id))""")
        self.con.commit()  # Sačuvaj izmene u bazi

    def dodaj_korisnika(self, ime, lozinka):
        # Pokušaj da dodaš novog korisnika u bazu
        try:
            self.cur.execute("INSERT INTO korisnici (korisnicko_ime, lozinka) VALUES (?, ?)", (ime, lozinka))
            self.con.commit()
            return True
        except:
            # Ako korisnicko ime već postoji, vrati False
            return False

    def proveri_prijavu(self, ime, lozinka):
        # Proveri da li postoje podaci za prijavu i vrati id korisnika
        self.cur.execute("SELECT id FROM korisnici WHERE korisnicko_ime=? AND lozinka=?", (ime, lozinka))
        rezultat = self.cur.fetchone()
        return rezultat[0] if rezultat else None

    def dodaj_transakciju(self, korisnik_id, tip, kategorija, iznos, opis):
        # Ubaci novu transakciju u bazu za korisnika
        self.cur.execute("INSERT INTO transakcije (korisnik_id, tip, kategorija, iznos, opis) VALUES (?, ?, ?, ?, ?)",
                         (korisnik_id, tip, kategorija, iznos, opis))
        self.con.commit()

    def dohvati_transakcije(self, korisnik_id, tip_filter=None, datum_od=None, datum_do=None):
        # Dohvati transakcije korisnika uz opcione filtere po tipu i datumu
        query = "SELECT tip, kategorija, iznos, opis, datum FROM transakcije WHERE korisnik_id=?"
        params = [korisnik_id]

        # Filter po tipu (prihod/rashod), osim ako je 'Svi'
        if tip_filter and tip_filter.lower() != "svi":
            query += " AND tip=?"
            params.append(tip_filter.lower())

        # Filter po datumu (od - do)
        if datum_od and datum_do:
            query += " AND datum BETWEEN ? AND ?"
            params.append(datum_od)
            params.append(datum_do)

        query += " ORDER BY datum DESC"  # Sortiraj po datumu opadajuće
        self.cur.execute(query, params)
        return self.cur.fetchall()


# PROZOR ZA PRIJAVU I REGISTRACIJU
class ProzorPrijava(QWidget):
    def __init__(self, baza):
        super().__init__()
        self.baza = baza
        self.setWindowTitle("Finansijski planer")
        self.setGeometry(500, 300, 350, 220)
        self.setMinimumSize(350, 220)

        raspored = QVBoxLayout()

        # Naslov aplikacije
        naslov = QLabel("Finansijski planer")
        naslov.setStyleSheet("font-size: 18px; font-weight: bold;")
        naslov.setAlignment(Qt.AlignCenter)

        # Polja za unos korisničkog imena i lozinke
        self.unos_ime = QLineEdit()
        self.unos_ime.setPlaceholderText("Korisničko ime")
        self.unos_lozinka = QLineEdit()
        self.unos_lozinka.setPlaceholderText("Lozinka")
        self.unos_lozinka.setEchoMode(QLineEdit.Password)  # Maskiranje lozinke

        # Dugme za prijavu
        dugme_prijava = QPushButton("Prijavi se")
        dugme_prijava.clicked.connect(self.prijava)

        # Dugme za registraciju
        dugme_registracija = QPushButton("Registruj se")
        dugme_registracija.clicked.connect(self.registracija)

        # Dodavanje elemenata u vertikalni raspored
        for el in [naslov, self.unos_ime, self.unos_lozinka, dugme_prijava, dugme_registracija]:
            raspored.addWidget(el)

        self.setLayout(raspored)

    def prijava(self):
        # Proverava korisničke podatke i otvara glavni prozor ako su ispravni
        ime = self.unos_ime.text().strip()
        lozinka = self.unos_lozinka.text().strip()
        id = self.baza.proveri_prijavu(ime, lozinka)

        if id:
            self.hide()
            self.glavni = GlavniProzor(self.baza, id, ime)
            self.glavni.showMaximized()
        else:
            QMessageBox.warning(self, "Greška", "Proverite korisničko ime i lozinku.")

    def registracija(self):
        # Registruje novog korisnika u bazu
        ime = self.unos_ime.text().strip()
        lozinka = self.unos_lozinka.text().strip()

        if self.baza.dodaj_korisnika(ime, lozinka):
            QMessageBox.information(self, "Uspeh", "Uspešno ste registrovani.")
        else:
            QMessageBox.warning(self, "Greška", "Korisničko ime već postoji.")


# GLAVNI PROZOR APLIKACIJE
class GlavniProzor(QMainWindow):
    def __init__(self, baza, korisnik_id, ime):
        super().__init__()
        self.baza = baza
        self.korisnik_id = korisnik_id
        self.setWindowTitle("Finansijski planer")
        self.setMinimumSize(800, 550)

        # Centralni widget i njegov raspored
        centralni = QWidget()
        self.setCentralWidget(centralni)
        raspored = QVBoxLayout()
        centralni.setLayout(raspored)

        # Poruka dobrodošlice korisniku
        dobrodoslica = QLabel(f" Dobrodošli, {ime}!")
        dobrodoslica.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        raspored.addWidget(dobrodoslica)

        # Labela za prikaz trenutnog stanja
        self.label_stanje = QLabel()
        self.label_stanje.setStyleSheet("font-size: 16px; color: #2E8B57; padding: 6px;")
        raspored.addWidget(self.label_stanje)

        # Tab widget za izbor između unosa i pregleda transakcija
        self.tabovi = QTabWidget()
        raspored.addWidget(self.tabovi)

        # ---- TAB 1: Unos nove transakcije ----
        tab_unos = QWidget()
        forma = QFormLayout()
        tab_unos.setLayout(forma)

        # ComboBox za izbor tipa transakcije
        self.tip = QComboBox()
        self.tip.addItems(["Prihod", "Rashod"])
        self.tip.currentIndexChanged.connect(self.promeni_kategorije)

        # ComboBox za kategorije, zavisno od tipa
        self.kategorija = QComboBox()
        self.kategorija.addItems(["Džeparac", "Stipendija", "Ostalo"])

        # Polja za unos iznosa i opisa
        self.iznos = QLineEdit()
        self.opis = QLineEdit()

        # Dugme za dodavanje transakcije
        dugme_dodaj = QPushButton("Sačuvaj transakciju")
        dugme_dodaj.clicked.connect(self.dodaj)

        # Dodavanje elemenata u formu
        forma.addRow("Tip:", self.tip)
        forma.addRow("Kategorija:", self.kategorija)
        forma.addRow("Iznos (RSD):", self.iznos)
        forma.addRow("Opis (opciono):", self.opis)
        forma.addRow("", dugme_dodaj)

        self.tabovi.addTab(tab_unos, " Nova transakcija")

        # ---- TAB 2: Pregled istorije transakcija ----
        tab_pregled = QWidget()
        pregled_layout = QVBoxLayout()
        tab_pregled.setLayout(pregled_layout)

        # Layout za filtere
        filteri_layout = QHBoxLayout()

        # Filter po tipu transakcije
        self.combo_tip_filter = QComboBox()
        self.combo_tip_filter.addItems(["Svi", "Prihod", "Rashod"])

        # Filter po datumu (od-do)
        self.datum_od = QDateEdit()
        self.datum_od.setCalendarPopup(True)
        self.datum_od.setDate(QDate.currentDate().addMonths(-1))

        self.datum_do = QDateEdit()
        self.datum_do.setCalendarPopup(True)
        self.datum_do.setDate(QDate.currentDate())

        # Dugme za primenu filtera
        dugme_filter = QPushButton("Primeni filter")
        dugme_filter.clicked.connect(self.osvezi_prikaz)

        # Dodavanje filtera u layout
        filteri_layout.addWidget(QLabel("Tip:"))
        filteri_layout.addWidget(self.combo_tip_filter)
        filteri_layout.addWidget(QLabel("Od:"))
        filteri_layout.addWidget(self.datum_od)
        filteri_layout.addWidget(QLabel("Do:"))
        filteri_layout.addWidget(self.datum_do)
        filteri_layout.addWidget(dugme_filter)

        # Tabela za prikaz transakcija
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(5)
        self.tabela.setHorizontalHeaderLabels(["Tip", "Kategorija", "Iznos", "Opis", "Datum"])
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Dodavanje filtera i tabele u glavni raspored taba za pregled
        pregled_layout.addLayout(filteri_layout)
        pregled_layout.addWidget(self.tabela)

        self.tabovi.addTab(tab_pregled, " Istorija transakcija")

        # Učitavanje i prikaz podataka pri pokretanju
        self.osvezi_prikaz()

    def promeni_kategorije(self):
        # Menja listu kategorija u zavisnosti od tipa transakcije
        self.kategorija.clear()
        if self.tip.currentText() == "Prihod":
            self.kategorija.addItems(["Džeparac", "Stipendija", "Uplata"])
        else:
            self.kategorija.addItems(["Hrana", "Prevoz", "Knjige", "Zabava", "Ostalo"])

    def dodaj(self):
        # Dodaje novu transakciju nakon validacije unosa
        try:
            iznos = float(self.iznos.text())
            if iznos <= 0:
                raise ValueError

            self.baza.dodaj_transakciju(self.korisnik_id, self.tip.currentText().lower(),
                                        self.kategorija.currentText(), iznos, self.opis.text())

            QMessageBox.information(self, "Uspeh", "Transakcija je uspešno sačuvana.")
            self.iznos.clear()
            self.opis.clear()
            self.osvezi_prikaz()
        except:
            QMessageBox.warning(self, "Greška", "Unesite ispravan iznos (broj veći od 0).")

    def osvezi_prikaz(self):
        # Osvežava prikaz tabele i trenutno stanje korisnika
        tip = self.combo_tip_filter.currentText()
        datum_od = self.datum_od.date().toString("yyyy-MM-dd")
        datum_do = self.datum_do.date().toString("yyyy-MM-dd")

        podaci = self.baza.dohvati_transakcije(self.korisnik_id, tip, datum_od, datum_do)

        self.tabela.setRowCount(len(podaci))

        prihod = 0
        rashod = 0

        # Popunjavanje tabele i računanje stanja
        for i, red in enumerate(podaci):
            for j, vrednost in enumerate(red):
                self.tabela.setItem(i, j, QTableWidgetItem(str(vrednost)))
            if red[0] == "prihod":
                prihod += float(red[2])
            elif red[0] == "rashod":
                rashod += float(red[2])

        stanje = prihod - rashod
        self.label_stanje.setText(f" Trenutno stanje: {stanje:.2f} RSD")


# GLAVNA PETLJA APLIKACIJE
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Stilizovanje aplikacije kroz CSS
    app.setStyleSheet("""
        QWidget { font-family: Segoe UI; font-size: 13px; }
        QLineEdit, QComboBox { padding: 6px; border-radius: 6px; border: 1px solid #888; }
        QPushButton {
            background-color: #3b5998;
            color: white;
            border-radius: 6px;
            padding: 8px;
        }
        QPushButton:hover {
            background-color: #2d4373;
        }
        QTableWidget {
            border: 1px solid #ccc;
        }
    """)

    baza = Baza()  # Kreiraj objekat baze podataka
    prozor = ProzorPrijava(baza)  # Kreiraj prozor za prijavu
    prozor.show()  # Prikaži prozor
    sys.exit(app.exec())  # Pokreni Qt aplikaciju

