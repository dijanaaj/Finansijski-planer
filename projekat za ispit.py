import sys, sqlite3
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate


# KLASA: Rad sa bazom podataka

class Baza:
    def __init__(self):
        # Povezivanje sa SQLite bazom podataka 'finansije.db'
        self.con = sqlite3.connect("finansije.db")
        self.cur = self.con.cursor()

        # Kreiranje tabele korisnici ako ne postoji
        # Polja: id (jedinstveni identifikator), korisnicko_ime (jedinstveno), lozinka
        self.cur.execute("""CREATE TABLE IF NOT EXISTS korisnici (
            id INTEGER PRIMARY KEY, korisnicko_ime TEXT UNIQUE, lozinka TEXT)""")

        # Kreiranje tabele transakcije ako ne postoji
        # Polja: id, korisnik_id (spoljni ključ ka korisnici),
        # tip (prihod/rashod), kategorija, iznos, opis, datum sa podrazumevanom vrednošću današnjeg datuma
        self.cur.execute("""CREATE TABLE IF NOT EXISTS transakcije (
            id INTEGER PRIMARY KEY, korisnik_id INTEGER, tip TEXT,
            kategorija TEXT, iznos REAL, opis TEXT, datum TEXT DEFAULT CURRENT_DATE,
            FOREIGN KEY(korisnik_id) REFERENCES korisnici(id))""")
        self.con.commit()  # Potvrđujemo izmene u bazi

    def dodaj_korisnika(self, ime, lozinka):
        # Pokušaj da se doda novi korisnik sa korisničkim imenom i lozinkom
        # Ako korisničko ime postoji, funkcija vraća False
        try:
            self.cur.execute("INSERT INTO korisnici (korisnicko_ime, lozinka) VALUES (?, ?)", (ime, lozinka))
            self.con.commit()
            return True
        except:
            return False

    def proveri_prijavu(self, ime, lozinka):
        # Proverava da li postoji korisnik sa zadatim imenom i lozinkom
        # Ako postoji, vraća ID korisnika, inače None
        self.cur.execute("SELECT id FROM korisnici WHERE korisnicko_ime=? AND lozinka=?", (ime, lozinka))
        rezultat = self.cur.fetchone()
        return rezultat[0] if rezultat else None

    def dodaj_transakciju(self, korisnik_id, tip, kategorija, iznos, opis):
        # Dodaje novu transakciju u bazu za određenog korisnika
        self.cur.execute("INSERT INTO transakcije (korisnik_id, tip, kategorija, iznos, opis) VALUES (?, ?, ?, ?, ?)",
                         (korisnik_id, tip, kategorija, iznos, opis))
        self.con.commit()

    def dohvati_transakcije(self, korisnik_id, tip_filter=None, datum_od=None, datum_do=None):
        # Dohvata transakcije za korisnika uz mogućnost filtriranja po tipu i datumu
        query = "SELECT tip, kategorija, iznos, opis, datum FROM transakcije WHERE korisnik_id=?"
        params = [korisnik_id]

        # Ako je odabran filter za tip osim 'Svi', dodajemo ga u upit
        if tip_filter and tip_filter.lower() != "svi":
            query += " AND tip=?"
            params.append(tip_filter.lower())

        # Ako su postavljeni datumski filteri, dodajemo uslov za opseg datuma
        if datum_od and datum_do:
            query += " AND datum BETWEEN ? AND ?"
            params.append(datum_od)
            params.append(datum_do)

        query += " ORDER BY datum DESC"  # Sortiranje po datumu opadajuće
        self.cur.execute(query, params)
        return self.cur.fetchall()

# PROZOR ZA PRIJAVU I REGISTRACIJU

class ProzorPrijava(QWidget):
    def __init__(self, baza):
        super().__init__()
        self.baza = baza
        self.setWindowTitle("Finansijski planer")
        self.setGeometry(500, 300, 350, 220)  # Pozicija i veličina prozora
        self.setMinimumSize(350, 220)  # Minimalna veličina prozora

        raspored = QVBoxLayout()  # Vertikalni raspored elemenata

        # Naslov aplikacije
        naslov = QLabel("Finansijski planer")
        naslov.setStyleSheet("font-size: 18px; font-weight: bold;")
        naslov.setAlignment(Qt.AlignCenter)

        # Polja za unos korisničkog imena i lozinke
        self.unos_ime = QLineEdit()
        self.unos_ime.setPlaceholderText("Korisničko ime")
        self.unos_lozinka = QLineEdit()
        self.unos_lozinka.setPlaceholderText("Lozinka")
        self.unos_lozinka.setEchoMode(QLineEdit.Password)  # Lozinka maskirana

        # Dugmad za prijavu i registraciju
        dugme_prijava = QPushButton("Prijavi se")
        dugme_prijava.clicked.connect(self.prijava)  # Povezivanje sa funkcijom za prijavu

        dugme_registracija = QPushButton("Registruj se")
        dugme_registracija.clicked.connect(self.registracija)  # Povezivanje sa funkcijom za registraciju

        # Dodavanje svih elemenata u vertikalni raspored
        for el in [naslov, self.unos_ime, self.unos_lozinka, dugme_prijava, dugme_registracija]:
            raspored.addWidget(el)

        self.setLayout(raspored)

    def prijava(self):
        # Funkcija koja proverava korisničke podatke i otvara glavni prozor
        ime = self.unos_ime.text().strip()
        lozinka = self.unos_lozinka.text().strip()
        id = self.baza.proveri_prijavu(ime, lozinka)

        if id:
            self.hide()  # Sakriva prozor prijave
            self.glavni = GlavniProzor(self.baza, id, ime)
            self.glavni.showMaximized()  # Otvara glavni prozor maksimizovan
        else:
            QMessageBox.warning(self, "Greška", "Proverite korisničko ime i lozinku.")

    def registracija(self):
        # Funkcija za registraciju novog korisnika
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
        self.setMinimumSize(800, 550)  # Minimalna veličina glavnog prozora

        centralni = QWidget()  # Centralni widget koji drži sve ostalo
        self.setCentralWidget(centralni)
        raspored = QVBoxLayout()
        centralni.setLayout(raspored)

        # Poruka dobrodošlice korisniku
        dobrodoslica = QLabel(f" Dobrodošli, {ime}!")
        dobrodoslica.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        raspored.addWidget(dobrodoslica)

        # Labela za prikaz trenutnog stanja (saldo)
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

        # ComboBox za izbor tipa transakcije: Prihod ili Rashod
        self.tip = QComboBox()
        self.tip.addItems(["Prihod", "Rashod"])
        self.tip.currentIndexChanged.connect(self.promeni_kategorije)  # Pri promeni tipa menja se lista kategorija

        # ComboBox za kategorije, koje zavise od tipa (prihod/rashod)
        self.kategorija = QComboBox()
        self.kategorija.addItems(["Džeparac", "Stipendija", "Ostalo"])

        # Polja za unos iznosa i opcionalnog opisa transakcije
        self.iznos = QLineEdit()
        self.opis = QLineEdit()

        # Dugme za dodavanje transakcije u bazu
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

        # Layout za filtere po tipu i datumu
        filteri_layout = QHBoxLayout()

        # ComboBox za izbor filtera tipa (Svi, Prihod, Rashod)
        self.combo_tip_filter = QComboBox()
        self.combo_tip_filter.addItems(["Svi", "Prihod", "Rashod"])

        # Dva QDateEdit polja za filtriranje po datumu (od - do)
        self.datum_od = QDateEdit()
        self.datum_od.setCalendarPopup(True)
        self.datum_od.setDate(QDate.currentDate().addMonths(-1))  # Podrazumevano na mesec dana unazad

        self.datum_do = QDateEdit()
        self.datum_do.setCalendarPopup(True)
        self.datum_do.setDate(QDate.currentDate())  # Podrazumevano današnji datum

        # Dugme koje pokreće filtriranje
        dugme_filter = QPushButton("Primeni filter")
        dugme_filter.clicked.connect(self.osvezi_prikaz)  # Osvježava tabelu sa primenjenim filterima

        # Dodavanje filtera u horizontalni raspored
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
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Kolone da se prilagođavaju veličini tabele

        # Dodavanje filtera i tabele u glavni raspored taba za pregled
        pregled_layout.addLayout(filteri_layout)
        pregled_layout.addWidget(self.tabela)

        self.tabovi.addTab(tab_pregled, " Istorija transakcija")

        # Inicijalno učitavanje podataka i prikaz
        self.osvezi_prikaz()

    def promeni_kategorije(self):
        # Funkcija koja menja dostupne kategorije u zavisnosti od tipa transakcije
        self.kategorija.clear()
        if self.tip.currentText() == "Prihod":
            self.kategorija.addItems(["Džeparac", "Stipendija", "Uplata"])
        else:
            self.kategorija.addItems(["Hrana", "Prevoz", "Knjige", "Zabava", "Ostalo"])

    def dodaj(self):
        # Funkcija koja dodaje novu transakciju nakon validacije unetih podataka
        try:
            iznos = float(self.iznos.text())
            if iznos <= 0:
                raise ValueError  # Iznos mora biti veći od nule

            # Dodavanje u bazu preko metode iz klase Baza
            self.baza.dodaj_transakciju(self.korisnik_id, self.tip.currentText().lower(),
                                        self.kategorija.currentText(), iznos, self.opis.text())

            QMessageBox.information(self, "Uspeh", "Transakcija je uspešno sačuvana.")
            self.iznos.clear()  # Čišćenje polja nakon unosa
            self.opis.clear()
            self.osvezi_prikaz()  # Osvježavanje prikaza sa novom transakcijom
        except:
            QMessageBox.warning(self, "Greška", "Unesite ispravan iznos (broj veći od 0).")

    def osvezi_prikaz(self):
        # Ova funkcija osvežava tabelu transakcija i prikazuje trenutno stanje

        # Preuzimanje filtera iz GUI polja
        tip = self.combo_tip_filter.currentText()
        datum_od = self.datum_od.date().toString("yyyy-MM-dd")
        datum_do = self.datum_do.date().toString("yyyy-MM-dd")

        # Dohvatanje filtriranih podataka iz baze
        podaci = self.baza.dohvati_transakcije(self.korisnik_id, tip, datum_od, datum_do)

        self.tabela.setRowCount(len(podaci))  # Postavljanje broja redova u tabeli

        prihod = 0
        rashod = 0

        # Popunjavanje tabele i računanje stanja
        for i, red in enumerate(podaci):
            for j, vrednost in enumerate(red):
                self.tabela.setItem(i, j, QTableWidgetItem(str(vrednost)))
            # Sabiranje prihoda i rashoda
            if red[0] == "prihod":
                prihod += float(red[2])
            elif red[0] == "rashod":
                rashod += float(red[2])

        # Izračunavanje i prikaz stanja
        stanje = prihod - rashod
        self.label_stanje.setText(f" Trenutno stanje: {stanje:.2f} RSD")


# GLAVNA PETLJA APLIKACIJE

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Stilizovanje aplikacije 
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

    baza = Baza()  # Kreiranje objekta baze
    prozor = ProzorPrijava(baza)  # Kreiranje prozora za prijavu
    prozor.show()  # Prikaz prozora
    sys.exit(app.exec())  # Pokretanje Qt petlje

