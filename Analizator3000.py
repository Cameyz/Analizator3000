import glob #biblioteka która używa Unixowych wyrażeń do szukania plików
import os
import re #moduł wyrażeń regularnych
from collections import defaultdict
from pathlib import Path
from datetime import datetime


# ========================
# MIEJSCE NA TABELE
# ========================

licznik_bledow_urzadzen = {} #tworzę słownik tak by każda zmienna miała swoje id
bledy_stclass = {} # klasa → kod → licznik
bledy_stclass_per_dziennik = {}  # (ID, data) → klasa → kod → liczba
globalne_bledy_stclass = {} # tutaj do podsumowani globalu
bledy_dyspensera_per_dziennik = {} #zbieram bledy dyspnsera
bledy_dyspensera_global = {}# tutaj podsumuje bledy globalne
transakcje_udane = {} # (urządzenie, data) -> liczba
transakcje_nieudane = {} # (urządzenie, data) -> liczba
transakcje_wplaty_udane = {} # (urządzenie, data) -> liczba
transakcje_wplaty_nieudane = {} # (urządzenie, data) -> liczba
czasy_wyplat_udane = defaultdict(list)
czasy_wyplat_nieudane = defaultdict(list)
czasy_wplat_udane = defaultdict(list)
czasy_wplat_nieudane = defaultdict(list)
czasy_wplat = {} # ⏱️ Czasy trwania transakcji
czasy_wyplat = {}
min_czas_udanych = {} # ⏱️ Min i max czas trwania dla udanych transakcji
max_czas_udanych = {}
czasy_trx_udane_wyplata = defaultdict(list)
czasy_trx_udane_wplata = defaultdict(list)

najkrotsza_wyplata = {}
najdluzsza_wyplata = {}
najkrotsza_wplata = {}
najdluzsza_wplata = {}
linie_startowe = {}  # (urzadzenie_id, data, typ, czas_trwania): linia_startu

wszystkie_linie = []

slownik_opisow_odmowy = {
    "365": "Nieudana autoryzacja",
    "366": "Brak odpowiedzi z banku",
    "367": "Transakcja zablokowana przez operatora",
    "368": "Odrzucenie przez limit dzienny",
    "369": "Odrzucenie przez kartę",
    "370": "Błąd komunikacji z systemem bankowym",
    "371": "Niewłaściwa kwota operacji",
    "372": "Zbyt wiele prób",
    "373": "Nieznany błąd terminala",
    "374": "Błąd systemu",
    "375": "Limit ilościowy przekroczony",
    "376": "Transakcja odrzucona z powodu bezpieczeństwa",
    "377": "Przekroczony czas operacji",
    "378": "Karta zastrzeżona",
    "379": "Niepoprawny PIN",
    "380": "Nieobsługiwany typ karty",
    "381": "Niewłaściwa wersja systemu",
    "382": "System w trybie serwisowym",
    "383": "Karta nieaktywna",
    "384": "Transakcja już zrealizowana",
    "385": "Operacja anulowana przez użytkownika",
    "386": "Przekroczono limit wypłat",
    "387": "Niedozwolona operacja",
    "388": "Transakcja przekracza limit karty",
    "389": "Brak środków",
    "390": "Nieznany typ operacji",
    "391": "Zbyt mała kwota operacji",
    "392": "Zbyt duża kwota operacji",
    "393": "Karta zablokowana",
    "394": "Nieautoryzowana karta",
    "395": "Nieobsługiwany bank",
    "396": "Transakcja odrzucona przez bank",
    "397": "Błąd formatowania danych",
    "398": "Nieznana odpowiedź banku",
    "399": "Błąd aplikacji bankowej",
    "400": "System chwilowo niedostępny",
    "401": "System zajęty",
    "402": "Przekroczono limit czasowy odpowiedzi",
    "403": "Transakcja zablokowana z przyczyn bezpieczeństwa",
    "404": "REFUSE OFF US",
    "424": "PROSZE WPROWADZIC INNA KWOTE",
    "426": "Błąd wszystkich kaset",
    "431": "BANKOTY NIE ZOSTALY WYPLACONE"
}


# ========================
# MIEJSCE NA FUNKCJĘ
# ========================


def formatuj_czas(sekundy):
    if sekundy is None:
        return "n/d"
    minuty = sekundy // 60
    sekundy = sekundy % 60
    return f"{minuty}m {sekundy}s"

def znajdz_czas(linia):
    # Format HH:MM:SS
    match = re.search(r"\b(\d{2}):(\d{2}):(\d{2})\b", linia)
    if match:
        godzina, minuta, sekunda = map(int, match.groups())
        return godzina * 3600 + minuta * 60 + sekunda

    # Format HH:MM (np. w linii typu: *968*18/04/2025*20:54*)
    match_alt = re.search(r"\*(\d{2}):(\d{2})\*", linia)
    if match_alt:
        godzina, minuta = map(int, match_alt.groups())
        return godzina * 3600 + minuta * 60

    return None

def oblicz_czas_trwania(start, koniec):
    """Zwraca czas trwania transakcji w sekundach."""
    if start is None or koniec is None:
        return None
    return koniec - start

def wczytaj_linie_z_pliku(plik): #funckja do wczytywania linni z plików
    try:
        with open(plik, "r", encoding="utf-8") as f:
            linie = f.readlines()
            print(f"✅ Odczytano {len(linie)} linii z pliku (UTF-8): {plik}")
            return linie
    except UnicodeDecodeError:
        try:
            with open(plik, "r", encoding="cp1250") as f:
                linie = f.readlines()
                print(f"✅ Odczytano {len(linie)} linii z pliku (CP1250): {plik}")
                return linie
        except Exception as e:
            print(f"❌ Błąd odczytu pliku {plik}: {e}")
            return None

def analizuj_transakcje(linie, urzadzenie_id, data, transakcje_udane, transakcje_nieudane, transakcje_wplaty_udane, transakcje_wplaty_nieudane):
    klucz = (urzadzenie_id, data)
    trx_slowa_udane = ["gotowka odebrana", "sprawdzenie salda", "banknoty odebrane", "status transakcji 6", "bankonty odebrano", "cdm-zakonczenie przyjecia gotowki"]
    trx_slowa_nieudane = ["trans. odrzucona", "brak reakcji klienta w czasie", "status transakcji 3", "status transakcji 1", "klient wybral 'cancel' - anulowanie transakcji", "blad", "deponowanie - blad", "timeout z stanu timeout", "klient wybral anulowanie transakcji"]
    trx_slowa_konczace = ["koniec operacji", "*koniec operacji*", "deponowanie - blad", "blad urzadzenia", "zdetektowano banknoty", "rozpoczeto retract", "reset nieudany", "koniec transakc"]

    transakcja_aktywna = False
    trx_status = "nieznany"
    ostatni_czas_w_linii = None
    czas_startu = None
    typ_transakcji = "wypłata"
    
    oczekiwanie_na_czas_startu = False  # 🆕 flaga oczekiwania na pierwszy poprawny czas

    for i, linia in enumerate(linie):
        linia_mala = linia.lower().strip()

        czas_w_linii = znajdz_czas(linia)

        # 🆕 jeśli oczekujemy na pierwszy czas PO rozpoczęciu transakcji
        if oczekiwanie_na_czas_startu and czas_w_linii:
            czas_startu = czas_w_linii
            oczekiwanie_na_czas_startu = False

        if any(slowo in linia_mala for slowo in ["rozpoczecie transakcji", "poczatek operacji", "*poczatek operacji*", "transakcja bez karty", "*transakcja bez karty*"]):
            transakcja_aktywna = True
            trx_status = "nieznany"
            oczekiwanie_na_czas_startu = True  # 🆕 oczekujemy na rzeczywisty start
            typ_transakcji = "wypłata"  # 🔁 zamiast przypisywać czas od razu

        if transakcja_aktywna and any(slowo in linia_mala for slowo in ["wplaty", "wpłaty", "wplata", "wpłata"]):
            typ_transakcji = "wpłata"

        if transakcja_aktywna and any(haslo in linia_mala for haslo in trx_slowa_udane):
            trx_status = "udana"

        if transakcja_aktywna and any(haslo in linia_mala for haslo in trx_slowa_nieudane):
            trx_status = "nieudana"

        if transakcja_aktywna and any(haslo in linia_mala for haslo in trx_slowa_konczace):
            czas_konca = znajdz_czas(linia)
            if czas_konca is not None and czas_startu is not None:
                czas_trwania = oblicz_czas_trwania(czas_startu, czas_konca)

                if trx_status == "udana":
                    if typ_transakcji == "wpłata":
                        czasy_wplat.setdefault(klucz, []).append(czas_trwania)
                        transakcje_wplaty_udane[klucz] = transakcje_wplaty_udane.get(klucz, 0) + 1
                        czasy_wplat_udane[klucz].append(czas_trwania)
                        czasy_trx_udane_wplata[klucz].append(czas_trwania)
                    else:
                        czasy_wyplat.setdefault(klucz, []).append(czas_trwania)
                        transakcje_udane[klucz] = transakcje_udane.get(klucz, 0) + 1
                        czasy_wyplat_udane[klucz].append(czas_trwania)
                        czasy_trx_udane_wyplata[klucz].append(czas_trwania)

                    if klucz not in min_czas_udanych or czas_trwania < min_czas_udanych[klucz]:
                        min_czas_udanych[klucz] = czas_trwania
                    if klucz not in max_czas_udanych or czas_trwania > max_czas_udanych[klucz]:
                        max_czas_udanych[klucz] = czas_trwania

                elif trx_status == "nieudana":
                    if typ_transakcji == "wpłata":
                        transakcje_wplaty_nieudane[klucz] = transakcje_wplaty_nieudane.get(klucz, 0) + 1
                        czasy_wplat_nieudane[klucz].append(czas_trwania)
                    else:
                        transakcje_nieudane[klucz] = transakcje_nieudane.get(klucz, 0) + 1
                        czasy_wyplat_nieudane[klucz].append(czas_trwania)

            # Reset transakcji
            transakcja_aktywna = False
            oczekiwanie_na_czas_startu = False  # 🆕 reset flagi
            czas_startu = None
            typ_transakcji = "wypłata"


def analizuj_bledy_stclass(linie, klucz, bledy_stclass_per_dziennik):
    wzorzec = re.compile(r"stClass=(\w+), stCode=(\w+)", re.IGNORECASE)

    for linia in linie:
        dopasowanie = wzorzec.search(linia)
        if dopasowanie:
            klasa = dopasowanie.group(1)
            kod = dopasowanie.group(2)

            if klucz not in bledy_stclass_per_dziennik:
                bledy_stclass_per_dziennik[klucz] = {}

            if klasa not in bledy_stclass_per_dziennik[klucz]:
                bledy_stclass_per_dziennik[klucz][klasa] = {}

            if kod not in bledy_stclass_per_dziennik[klucz][klasa]:
                bledy_stclass_per_dziennik[klucz][klasa][kod] = 1
            else:
                bledy_stclass_per_dziennik[klucz][klasa][kod] += 1

def analizuj_bledy_dyspensera(linie, klucz, bledy_dyspensera_per_dziennik):
    wzorzec_dyspensera = re.compile(r"BLAD Dyspensera: (\w{8}) (\w{8})", re.IGNORECASE)

    for linia in linie:
        dopasowanie = wzorzec_dyspensera.search(linia)
        if dopasowanie:
            pelna_klasa = dopasowanie.group(1)
            kod = dopasowanie.group(2)
            klasa = pelna_klasa[-4:]

            if klucz not in bledy_dyspensera_per_dziennik:
                bledy_dyspensera_per_dziennik[klucz] = {}

            if klasa not in bledy_dyspensera_per_dziennik[klucz]:
                bledy_dyspensera_per_dziennik[klucz][klasa] = {}

            if kod not in bledy_dyspensera_per_dziennik[klucz][klasa]:
                bledy_dyspensera_per_dziennik[klucz][klasa][kod] = 1
            else:
                bledy_dyspensera_per_dziennik[klucz][klasa][kod] += 1

def analizuj_bledy(linie, klucz, nazwa_pliku, data, licznik_bledow_urzadzen, wykluczenia):
    for i, linia in enumerate(linie):
        linia_lower = linia.lower()
        if any(keyword in linia_lower for keyword in ["stcode", "rejcode", "error", "blad", "rcode", "aplikacja wylaczona", "gooutofservice", "brak reakcji klienta w czasie", "status transakcji 3", "status transakcji 1", "blad", "deponowanie - blad", "timeout z stanu timeout"]):
            if any(wyklucz in linia_lower for wyklucz in wykluczenia):
                continue

            if klucz not in licznik_bledow_urzadzen:
                licznik_bledow_urzadzen[klucz] = 0

            print(f"🛑 [{data}] {nazwa_pliku} | Linia {i+1}: {linia.strip()}")
            licznik_bledow_urzadzen[klucz] += 1

def znajdz_id_urzadzenia(linie, nazwa_pliku):
    # Szukamy wzorca typu RNET1234, PNETB001, SGBA0001 itd.
    for linia in linie:
        match = re.search(r"\b([A-Z]{4}[A-Z0-9]{4})\b.*TRAN:", linia)
        if match:
            return match.group(1)
        match2 = re.search(r"/([A-Z]{4}[A-Z0-9]{4})->", linia)
        if match2:
            return match2.group(1)

    # Jeśli nie znaleziono – próbujemy z nazwy pliku
    nazwa = Path(nazwa_pliku).name
    match3 = re.match(r"([A-Z]{4}[A-Z0-9]{4})", nazwa)
    if match3:
        return match3.group(1)

    # Jeśli nadal nie znaleziono
    return "Nie odczytano numeru"

def znajdz_date_z_linii(linie, nazwa_pliku):
    wzorce_dat = [
        r"\b(\d{4})-(\d{2})-(\d{2})\b",      # 2025-04-08
        r"\b(\d{2})-(\d{2})-(\d{2})\b",      # 08-04-25
        r"\b(\d{2})/(\d{2})/(\d{4})\b",      # 08/04/2025
        r"\b(\d{2})\.(\d{2})\.(\d{4})\b",    # 24.03.2025
    ]

    for linia in linie:
        for wzorzec in wzorce_dat:
            dopasowanie = re.search(wzorzec, linia)
            if dopasowanie:
                try:
                    if len(dopasowanie.groups()) == 3:
                        g1, g2, g3 = dopasowanie.groups()
                        if len(g1) == 4:  # YYYY-MM-DD
                            return f"{g1}-{g2}-{g3}"
                        elif len(g3) == 4:  # DD.MM.YYYY lub DD/MM/YYYY
                            return f"{g3}-{g2}-{g1}"
                        else:  # np. 08-04-25 (rok dwucyfrowy)
                            return f"20{g3}-{g2}-{g1}"
                except:
                    continue

    # Jeśli nic nie znaleziono, to próbujemy z nazwy pliku
    dopasowanie = re.search(r"(\d{4})-(\d{2})-(\d{2})", nazwa_pliku)
    if dopasowanie:
        return f"{dopasowanie.group(1)}-{dopasowanie.group(2)}-{dopasowanie.group(3)}"

    return "Nie odczytano daty"


def przetworz_linie(nazwa_pliku, linie): #funckja do liczenia trx i błędów 
    urzadzenie_id = znajdz_id_urzadzenia(linie, nazwa_pliku)
    data = znajdz_date_z_linii(linie, nazwa_pliku)
    klucz = (urzadzenie_id, data)
    wykluczenia = ["no errors", "when no errors", "error -1", "chip contact error 1", "enter blik code", "receipt not available", "blad emv(dane niepoprawne lub niepelne) ctls"]

    analizuj_transakcje(linie, urzadzenie_id, data, transakcje_udane, transakcje_nieudane, transakcje_wplaty_udane, transakcje_wplaty_nieudane)
    analizuj_bledy_stclass(linie, klucz, bledy_stclass_per_dziennik)
    analizuj_bledy_dyspensera(linie, klucz, bledy_dyspensera_per_dziennik)
    analizuj_bledy(linie, klucz, nazwa_pliku, data, licznik_bledow_urzadzen, wykluczenia)

def znajdz_i_pokaz_transakcje_szczegolowe(lista_plikow_z_liniami):
    wszystkie_transakcje = []

    for nazwa_pliku, linie in lista_plikow_z_liniami:
        transakcja = []
        transakcja_aktywna = False
        czas_startu = None
        trx_typ = "wypłata"
        ostatni_czas_w_linii = None
        oczekiwanie_na_czas_startu = False  # 🆕 dodano flagę jak w analizuj_transakcje

        for i, linia in enumerate(linie):
            linia_mala = linia.lower()
            czas_w_linii = znajdz_czas(linia)

            if czas_w_linii is not None:
                ostatni_czas_w_linii = czas_w_linii  # 🆕 zapamiętaj ostatni znany czas

            if any(slowo in linia_mala for slowo in [
                "rozpoczecie transakcji", "poczatek operacji", "*poczatek operacji*",
                "transakcja bez karty", "*transakcja bez karty*"
            ]):
                transakcja_aktywna = True
                oczekiwanie_na_czas_startu = True  # 🆕 oczekujemy na pierwszy realny czas
                transakcja = [(i, linia.strip())]
                trx_typ = "wypłata"
                czas_startu = None  # 🆕 reset

            elif transakcja_aktywna:
                transakcja.append((i, linia.strip()))

                 # 🆕 przypisujemy pierwszy czas po starcie transakcji
                if oczekiwanie_na_czas_startu and czas_w_linii:
                    czas_startu = czas_w_linii
                    oczekiwanie_na_czas_startu = False

                if any(w in linia_mala for w in ["wplaty", "wpłaty", "wplata", "wpłata"]):
                    trx_typ = "wpłata"

                if any(slowo in linia_mala for slowo in [
                    "koniec operacji", "koniec transakc", "*koniec operacji*", "*koniec transakc*"
                ]):
                    czas_konca = czas_w_linii if czas_w_linii is not None else ostatni_czas_w_linii  # 🆕 fallback
                    if czas_startu and czas_konca:
                        czas_trwania = czas_konca - czas_startu
                        wszystkie_transakcje.append({
                            "plik": nazwa_pliku,
                            "linia_start": transakcja[0][0] + 1,
                            "czas_trwania": czas_trwania,
                            "typ": trx_typ,
                            "linie": transakcja
                        })
                    transakcja_aktywna = False
                    oczekiwanie_na_czas_startu = False  # 🆕 reset flagi

    if not wszystkie_transakcje:
        print("❌ Nie znaleziono żadnych zakończonych transakcji.")
        return

    def pokaz_transakcje(naj, opis):
        print(f"\n📌 {opis} | z dziennika {naj['plik']} zaczynająca się od linii {naj['linia_start']}:")
        print("─" * 80)
        for _, linia in naj['linie']:
            print(linia)
        print(f"⏱️ Czas trwania: {formatuj_czas(naj['czas_trwania'])}")

    # wybierz i pokaż
    for typ in ["wypłata", "wpłata"]:
        trx_danego_typu = [t for t in wszystkie_transakcje if t["typ"] == typ]
        if trx_danego_typu:
            najkrotsza = min(trx_danego_typu, key=lambda t: t["czas_trwania"])
            najdluzsza = max(trx_danego_typu, key=lambda t: t["czas_trwania"])
            pokaz_transakcje(najkrotsza, f"Najkrótsza transakcja {typ}")
            pokaz_transakcje(najdluzsza, f"Najdłuższa transakcja {typ}")


def znajdz_kody_odrzuconych_transakcji(lista_plikow_z_liniami):
    kody_odrzucen = defaultdict(lambda: {"opis": None, "ilosc": 0})

    # Wzorce
    wzorce = [
        r"TRANS\. ODRZUCONA: \((\d+) ([^\)]+)\)",       # ************XXXX TRANS. ODRZUCONA: (424 OPIS)
        r"TRANS\. ODRZUCONA: \((\d+)\)",                # ************XXXX TRANS. ODRZUCONA: (426)
        r"TRANS\. ODRZUCONA: \((\d+)\) ([^\n]*)"        # TRANSAKCJA BLIK TRANS. ODRZUCONA: (404) OPIS
    ]

    for nazwa_pliku, linie in lista_plikow_z_liniami:
        for linia in linie:
            for wzorzec in wzorce:
                match = re.search(wzorzec, linia)
                if match:
                    kod = match.group(1)
                    opis = match.group(2).strip() if len(match.groups()) > 1 else "Brak opisu"
                    kody_odrzucen[kod]["opis"] = opis or kody_odrzucen[kod]["opis"]
                    kody_odrzucen[kod]["ilosc"] += 1
                    break  # Jeśli dopasowano jeden wzorzec, pomiń resztę

    # Wyświetlenie podsumowania
    print("\n📊 Podsumowanie kodów odrzuconych transakcji:")
    print("Kod | Opis                                 | Liczba wystąpień")
    print("-" * 65)

    for kod, dane in sorted(kody_odrzucen.items(), key=lambda x: x[1]["ilosc"], reverse=True):
        opis = dane["opis"]
        if not opis or opis == "Brak opisu":
            opis = slownik_opisow_odmowy.get(kod, "! Brak opisu w bazie")
        print(f"{kod:<4} | {opis:<50} | {dane['ilosc']:<20}")



# ========================
# WYKONANIE 
# ========================

os.chdir("D:/Projekty/Python/Analizator3000") #zmieniam mu na siłę miejsce odczytu plików
print("KATALOG: ", os.getcwd()) #testowo do sprawdzania ścieżki odczytu plików, mogę później usunąć
sciezki = glob.glob("Dzienniki/*.txt") + glob.glob("Dzienniki/*.jrn") #zapisywanie scieżek do plików 

#odczytywanie plików i ich kodowania

print("Znaleziono plików:", len(sciezki)) #sprawdzamy ile jest tych plików
for plik in sciezki: #pętla wypisze mi ścieżki do plików
    print(plik)
    linie = wczytaj_linie_z_pliku(plik)
    nazwa = Path(plik).name
    przetworz_linie(nazwa, linie) #Silnik programu, najpier tabele i zmienne globalne później funkcję wykonujące
    wszystkie_linie.append((nazwa, linie))  # 💾 dodaj nazwę i linie


#wyświetlam wynik podsumowania ilości błędów dla kazdego z plików

print("\n📊 Podsumowanie błędów:") 
for (urz, data), liczba in licznik_bledow_urzadzen.items():
    print(f"➡️  [{data}] {urz}: {liczba} błędów")

#wyświetlam wynik podsumowania jakie klasy błedów znaleziono ile razy z podziałem na dni

print("\n📊 Błedy DN wg stClass/stCode:")
for (urz, data), klasy in bledy_stclass_per_dziennik.items():
    print(f"\n📅 {data} | 🏧 {urz}")
    for klasa, kody in klasy.items():
        print(f"🔧 Klasa: {klasa}")
        for kod, ile_razy in kody.items():
            print(f"⚙️  Kod: {kod} → {ile_razy}x")

            # Zbieramy do sumy globalnej znalezionych błędów
            if klasa not in globalne_bledy_stclass:
                globalne_bledy_stclass[klasa] = {}
            if kod not in globalne_bledy_stclass[klasa]:
                globalne_bledy_stclass[klasa][kod] = 0
            globalne_bledy_stclass[klasa][kod] += ile_razy

#wyświetlam wynik podsumowania jakie klasy błedów znaleziono

print("\n⚠️  W badanym okresie łacznie stClass/stCode:\n")
for klasa, kody in globalne_bledy_stclass.items():
    print(f"🔧 Klasa: {klasa}")
    for kod, ile_razy in kody.items():
        print(f"⚙️  Kod: {kod} → {ile_razy}x")

#wyświetlam wynik podsumowania jakie klasy błedów znaleziono dla dyspnsera
print("\n📊 Podsumowanie błędów dyspensera:")
for (urz, data), klasy in bledy_dyspensera_per_dziennik.items():
    print(f"\n📅 {data} | 🏧 {urz}")
    for klasa, kody in klasy.items():
        print(f"🔧 Klasa: {klasa}")
        for kod, ile_razy in kody.items():
            print(f"⚙️  Kod: {kod} → {ile_razy}x")

# Globalna tabela: klasa → kod → liczba
bledy_dyspensera_global = defaultdict(lambda: defaultdict(int))

# Przepisujemy dane z wersji per dziennik do globalnej
for klasy in bledy_dyspensera_per_dziennik.values():
    for klasa, kody in klasy.items():
        for kod, ile in kody.items():
            bledy_dyspensera_global[klasa][kod] += ile

# Wyświetlenie globalnego podsumowania
print("\n⚠️  W badanym okresie łacznie błędów dyspensera:")
for klasa, kody in bledy_dyspensera_global.items():
    print(f"🔧 Klasa: {klasa}")
    for kod, ile in kody.items():
        print(f"⚙️  Kod: {kod} → {ile}x")

# Wyświetlanie podsumowania znalezionych powdów odrzuceń przez CC

znajdz_kody_odrzuconych_transakcji(wszystkie_linie)

# 📊 PODSUMOWANIE TRANSAKCJI (wpłaty i wypłaty, czasy, sukcesy i porażki):

print("\n📊 PODSUMOWANIE TRANSAKCJI (wpłaty i wypłaty, czasy, sukcesy i porażki):\n")

col_widths = {
    "id": 10,
    "data": 12,
    "wyp_ok": 8,
    "wyp_fail": 8,
    "wpl_ok": 8,
    "wpl_fail": 8,
    "razem": 10,
    "sred_wyp": 12,
    "sred_wpl": 12,
    "min_wyp": 12,
    "max_wyp": 12,
    "min_wpl": 12,
    "max_wpl": 12,
}

# 🧾 Nagłówek
naglowek = (
    f"{'ID':<{col_widths['id']}} {'Data':<{col_widths['data']}} "
    f"{'Wypł. ✅':>{col_widths['wyp_ok']}} {'Wypł. ❌':>{col_widths['wyp_fail']}} "
    f"{'Wpł. ✅':>{col_widths['wpl_ok']}} {'Wpł. ❌':>{col_widths['wpl_fail']}} "
    f"{'📋  Razem':>{col_widths['razem']}} "
    f"{'⏱️  Śr. wypł.':>{col_widths['sred_wyp']}} {'⏱️  Śr. wpł.':>{col_widths['sred_wpl']}} "
    f"{'⏱️  Min wypł.':>{col_widths['min_wyp']}} {'⏱️  Max wypł.':>{col_widths['max_wyp']}} "
    f"{'⏱️  Min wpł.':>{col_widths['min_wpl']}} {'⏱️  Max wpł.':>{col_widths['max_wpl']}}"
)
print(naglowek)
print("-" * len(naglowek))

# 🧮 Wiersze danych
for (urz_id, data) in sorted(set().union(
    transakcje_udane.keys(), transakcje_nieudane.keys(),
    transakcje_wplaty_udane.keys(), transakcje_wplaty_nieudane.keys()
)):
    udane = transakcje_udane.get((urz_id, data), 0)
    nieudane = transakcje_nieudane.get((urz_id, data), 0)
    wp_udane = transakcje_wplaty_udane.get((urz_id, data), 0)
    wp_nieudane = transakcje_wplaty_nieudane.get((urz_id, data), 0)
    razem = udane + nieudane + wp_udane + wp_nieudane

    wyplaty_czasy = czasy_trx_udane_wyplata.get((urz_id, data), [])
    sredni_wypl = formatuj_czas(sum(wyplaty_czasy) // len(wyplaty_czasy)) if wyplaty_czasy else "-"
    min_wypl = formatuj_czas(min(wyplaty_czasy)) if wyplaty_czasy else "-"
    max_wypl = formatuj_czas(max(wyplaty_czasy)) if wyplaty_czasy else "-"

    wplaty_czasy = czasy_trx_udane_wplata.get((urz_id, data), [])
    sredni_wpl = formatuj_czas(sum(wplaty_czasy) // len(wplaty_czasy)) if wplaty_czasy else "-"
    min_wpl = formatuj_czas(min(wplaty_czasy)) if wplaty_czasy else "-"
    max_wpl = formatuj_czas(max(wplaty_czasy)) if wplaty_czasy else "-"

    print(
        f"{urz_id:<{col_widths['id']}} {data:<{col_widths['data']}} "
        f"{udane:>{col_widths['wyp_ok']}} {nieudane:>{col_widths['wyp_fail']}} "
        f"{wp_udane:>{col_widths['wpl_ok']}} {wp_nieudane:>{col_widths['wpl_fail']}} "
        f"{razem:>{col_widths['razem']}} "
        f"{sredni_wypl:>{col_widths['sred_wyp']}} {sredni_wpl:>{col_widths['sred_wpl']}} "
        f"{min_wypl:>{col_widths['min_wyp']}} {max_wypl:>{col_widths['max_wyp']}} "
        f"{min_wpl:>{col_widths['min_wpl']}} {max_wpl:>{col_widths['max_wpl']}}"
    )

print("\n")
znajdz_i_pokaz_transakcje_szczegolowe(wszystkie_linie)
print("\n")


