import glob #biblioteka która używa Unixowych wyrażeń do szukania plików
import os
import re #moduł wyrażeń regularnych
from collections import defaultdict

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

os.chdir("D:/Projekty/Python/Analizator3000") #zmieniam mu na siłę miejsce odczytu plików
print("KATALOG: ", os.getcwd()) #testowo do sprawdzania ścieżki odczytu plików, mogę później usunąć
sciezki = glob.glob("Dzienniki/*.txt") + glob.glob("Dzienniki/*.jrnl") #zapisywanie scieżek do plików 

#odczytywanie plików i ich kodowania

print("Znaleziono plików:", len(sciezki)) #sprawdzamy ile jest tych plików
for plik in sciezki: #pętla wypisze mi ścieżki do plików
    print(plik) #generuje scieżkę dla każdego pliku
    try:
        with open(plik, "r", encoding="utf-8") as f:
            linie = f.readlines()
            print(f"✅ Odczytano {len(linie)} linii z pliku (UTF-8): {plik}")
    except UnicodeDecodeError:
        try:
            with open(plik, "r", encoding="cp1250") as f:
                linie = f.readlines()
                print(f"✅ Odczytano {len(linie)} linii z pliku (CP1250): {plik}")
        except Exception as e:
            print(f"❌ Błąd odczytu pliku {plik}: {e}")
            continue  # przejdź do kolejnego pliku, by nie zatrzymać programu

#Silnik programu, najpier tabele i zmienne globalne później funkcję wykonujące

    wykluczenia = ["no errors", "when no errors", "error -1", "chip contact error 1", "enter blik code"]   #UWAGA!!! tylko małe litery - lista słów do wykluczeń
 
    #lista słów świadczących o udanej trx
    trx_slowa_udane = ["gotowka odebrana", "sprawdzenie salda", "banknoty odebrane", "status transakcji 6", "bankonty odebrano"] 

    """
    Status transakcji 6 - to kumnikat po wpłacie na DN, trx ok
    """

    #lista słów świadcząca i nie udanej trx
    trx_slowa_nieudane = ["trans. odrzucona","brak reakcji klienta w czasie", "status transakcji 3", "Status transakcji 1", "Klient wybral 'cancel' - anulowanie transakcji", "blad", "deponowanie - blad"]

    """
    Status transakcji 1 - to anulowanie
    Status transakcji 3 - to błąd przy wpłacie
    """
    trx_slowa_konczace = ["koniec operacji", "deponowanie - blad", "blad urzadzenia", "zdetektowano banknoty", "rozpoczeto retract", "reset nieudany", "koniec transakc"]  # dodasz więcej jak będzie trzeba

    transakcja_aktywna = False
    trx_status = "nieznany"

    from pathlib import Path
    nazwa_pliku = Path(plik).name #pobieram nazwe pliku bez scieżki (żeby było czytelniej)
    urzadzenie_id = Path(plik).name[:8] #zaczytuje 8 pierwszych znaków jako ID bankomatu - może niedziałac jak plik będzie miał inne nazewnictwo 
    data = nazwa_pliku.split("_")[1] # zakładamy format gdzie data jest ZAWSZE w środku nazwy inaczej data nie będzie działać
    klucz = (urzadzenie_id, data) #klucz bedzie rozdzialał dane z różnych plików na podsatwie ID i daty

    for i, linia in enumerate(linie):

        #SPRAWDZANIE TRX
        linia_mala = linia.lower().strip()

        # Rozpoznawanie rozpoczęcia transakcji
        if "rozpoczecie transakcji" in linia_mala or "poczatek operacji" in linia_mala:
            transakcja_aktywna = True
            trx_status = "nieznany"
            trx_typ="wypłata" #domyślnie każda trx to wypłata

        if "wplaty" in linia_mala: #chyba że ma słowo wpłata to zmienimy jej typ
                trx_typ="wpłata"   
        
        # Sprawdzanie słów świadczących o udanej transakcji
        if transakcja_aktywna and any(haslo in linia_mala for haslo in trx_slowa_udane):
            trx_status = "udana"
            

        # Sprawdzanie słów świadczących o nieudanej transakcji
        if transakcja_aktywna and any(haslo in linia_mala for haslo in trx_slowa_nieudane):
            trx_status = "nieudana"

        # Rozpoznawanie zakończenia transakcji
        if transakcja_aktywna and ("koniec transakc" in linia_mala or "koniec operacji" in linia_mala):
            klucz = (urzadzenie_id, data)
            if trx_status == "udana":
                if trx_typ == "wpłata":
                    transakcje_wplaty_udane[klucz] = transakcje_wplaty_udane.get(klucz, 0) +1
                else:
                    transakcje_udane[klucz] = transakcje_udane.get(klucz, 0) + 1
            elif trx_status == "nieudana":
                if trx_typ == "wpłata":
                    transakcje_wplaty_nieudane[klucz] = transakcje_wplaty_nieudane.get(klucz, 0) + 1
                else:
                    transakcje_nieudane[klucz] = transakcje_nieudane.get(klucz, 0) + 1
            else:
                # nie zliczamy nieokreślonych transakcji
                pass
            transakcja_aktywna = False  # kończymy śledzenie tej transakcji
       

        # Szukanie błędów
        if any(keyword in linia.lower() for keyword in ["stcode", "rejcode", "error", "blad", "rcode", "aplikacja wylaczona", "gooutofservice"]): #szukam słów kluczowych by wypisać je w liście
                
                if any(wyklucz in linia.lower() for wyklucz in wykluczenia):
                    continue #jak nie zawiera takich słów z wykluczeń to zostanie wyświetlone
                
                if klucz not in licznik_bledow_urzadzen:
                    licznik_bledow_urzadzen[klucz] = 0 #do słownika dodaje kluczę (nazwe urządzenia i datę) i ilość błędów (na start to 0)
                
                print(f"🛑 [{data}] {nazwa_pliku} | Linia {i+1}: {linia.strip()}")
                licznik_bledow_urzadzen[klucz] += 1 #jeśli wykona się powyższy print (czyli znajdzie się błąd, zwieksze licznik błedów w słowniku o 1)
                
        #SZUKANIE stClass oraz stCode w dzienniku !!!!!!!!!!!!!!!!!!!!!!!!

        wzorzec = r"stClass=(\w+), stCode=(\w+)"
        dopasowanie = re.search(wzorzec, linia)

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

        # Sprawdznie błędów dypsnsera !!!!!!!!!!!!!!!!!!!!!!!!

        wzorzec_dyspensera = r"BLAD Dyspensera: (\w{8}) (\w{8})"
        dop_dysp = re.search(wzorzec_dyspensera, linia)

        if dop_dysp:
            pelna_klasa = dop_dysp.group(1)
            kod = dop_dysp.group(2)
            klasa = pelna_klasa[-4:]

            if (urzadzenie_id, data) not in bledy_dyspensera_per_dziennik:
                bledy_dyspensera_per_dziennik[(urzadzenie_id, data)] = {}

            if klasa not in bledy_dyspensera_per_dziennik[(urzadzenie_id, data)]:
                bledy_dyspensera_per_dziennik[(urzadzenie_id, data)][klasa] = {}

            if kod not in bledy_dyspensera_per_dziennik[(urzadzenie_id, data)][klasa]:
                bledy_dyspensera_per_dziennik[(urzadzenie_id, data)][klasa][kod] = 1
            else:
                bledy_dyspensera_per_dziennik[(urzadzenie_id, data)][klasa][kod] += 1


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

# Wyświetlanie podsumowania transkacji

print("\n⚠️   Podsumowanie transakcji z podziałem na typy (wpłaty/wypłaty):")
print(f"{'ID urządzenia':<12} {'Data':<12} {'✅ Wypłaty':<10} {'❌ Wypłaty':<10} {'✅ Wpłaty':<10} {'❌ Wpłaty':<10} {'📋 Razem':<10}") #:<12 deklaruje ilośc miejsc w danym polu
print("-" * 80)

wszystkie_klucze_typy = set(transakcje_udane.keys()) | set(transakcje_nieudane.keys()) | set(transakcje_wplaty_udane.keys()) | set(transakcje_wplaty_nieudane.keys())

for urzadzenie_id, data in sorted(wszystkie_klucze_typy):
    wyp_ud = transakcje_udane.get((urzadzenie_id, data), 0)
    wyp_nie = transakcje_nieudane.get((urzadzenie_id, data), 0)
    wpl_ud = transakcje_wplaty_udane.get((urzadzenie_id, data), 0)
    wpl_nie = transakcje_wplaty_nieudane.get((urzadzenie_id, data), 0)
    suma = wyp_ud + wyp_nie + wpl_ud + wpl_nie
    print(f"{urzadzenie_id:<12} {data:<12} {wyp_ud:<12} {wyp_nie:<12} {wpl_ud:<12} {wpl_nie:<12} {suma:<10}")


print("\n")


