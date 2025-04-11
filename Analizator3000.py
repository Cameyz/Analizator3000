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

# CZYTANIE BŁĘDÓW:

    wykluczenia = ["no errors", "when no errors", "error -1", "chip contact error 1", "enter blik code"]   #UWAGA!!! tylko małe litery

    for i, linia in enumerate(linie):
        if any(keyword in linia.lower() for keyword in ["stcode", "rejcode", "error", "blad", "rcode", "aplikacja wylaczona", "gooutofservice"]): #szukam słów kluczowych by wypisać je w liście
                
                if any(wyklucz in linia.lower() for wyklucz in wykluczenia):
                    continue #jak nie zawiera takich słów z wykluczeń to zostanie wyświetlone
                
                from pathlib import Path
                nazwa_pliku = Path(plik).name #pobieram nazwe pliku bez scieżki (żeby było czytelniej)
                urzadzenie_id = Path(plik).name[:8] #zaczytuje 8 pierwszych znaków jako ID bankomatu - może niedziałac jak plik będzie miał inne nazewnictwo 
                
                data = nazwa_pliku.split("_")[1] # zakładamy format gdzie data jest ZAWSZE w środku nazwy inaczej data nie będzie działać
                klucz = (urzadzenie_id, data) #klucz bedzie rozdzialał dane z różnych plików na podsatwie ID i daty

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


#from collections import defaultdict
#
# Przykładowe dane z błędami dyspensera
#linie_dyspensera = [
#    "BLAD Dyspensera: 00006434 0000004C 00000000",
#    "BLAD Dyspensera: 00006434 0000004C 00000000",
#    "BLAD Dyspensera: 00006500 000000FF 00000000",
#    "BLAD Dyspensera: 00006434 0000004C 00000000",
#    "BLAD Dyspensera: 00006500 000000AA 00000000"
#]
#
# słownik zagnieżdżony: klasa → kod → liczba
#bledy_dyspensera = defaultdict(lambda: defaultdict(int))
#
# wzorzec do wyciągania klasy i kodu
#wzorzec_dyspnser = r"BLAD Dyspensera: (\w{8}) (\w{8})"
#
#for linia in linie_dyspensera:
#    dopasowanie = re.search(wzorzec_dyspnser, linia)
#    if dopasowanie:
#        pelna_klasa = dopasowanie.group(1)
#        klasa = pelna_klasa[-4:]  # ostatnie 4 znaki
#        kod = dopasowanie.group(2)
#        bledy_dyspensera[klasa][kod] += 1
#
#import pandas as pd
# Zamiana słownika do DataFrame dla przejrzystości
#tabela = []
#for klasa, kody in bledy_dyspensera.items():
#    for kod, ilosc in kody.items():
#        tabela.append((klasa, kod, ilosc))
#
#df = pd.DataFrame(tabela, columns=["Klasa", "Kod błędu", "Ilość wystąpień"])
#
#print("\n📊 Podsumowanie błędów dyspensera:\n")
#print(df.to_string(index=False))

print("\n")


