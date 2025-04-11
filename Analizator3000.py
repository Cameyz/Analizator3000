import glob #biblioteka która używa Unixowych wyrażeń do szukania plików
import os
import re #moduł wyrażeń regularnych

licznik_bledow_urzadzen = {} #tworzę słownik tak by każda zmienna miała swoje id
bledy_stclass = {} # klasa → kod → licznik
bledy_stclass_per_dziennik = {}  # (ID, data) → klasa → kod → liczba
globalne_bledy_stclass = {} # tutaj do podsumowani globalu

os.chdir("D:/Projekty/Python/Analizator3000") #zmieniam mu na siłę miejsce odczytu plików
print("KATALOG: ", os.getcwd()) #testowo do sprawdzania ścieżki odczytu plików, mogę później usunąć
sciezki = glob.glob("Dzienniki/*.txt") + glob.glob("Dzienniki/*.jrnl") #zapisywanie scieżek do plików 

print("Znaleziono plików:", len(sciezki)) #sprawdzamy ile jest tych plików
for plik in sciezki: #pętla wypisze mi ścieżki do plików
    print(plik) #generuje scieżkę dla każdego pliku

for plik in sciezki: #dla każdego pliku z listy scieżek
    print(f"\n📄 Przetwarzam błędy pliku: {plik}")
    
    #zamaskowałem część kodu testowego
try:
    with open(plik, "r", encoding="utf-8") as f: #otwiram plik (po konkretnej ścieżce) z możlwiwością odczytu R i kodowaniem utf8
        linie = f.readlines()
except UnicodeDecodeError: 
    with open(plik, "r", encoding="cp1250", errors="replace") as f: #Przy wgraniu większej ilości plików okazało się że częśc z nich może mnieć inne kodowanie. Powyższe wybiera domyślnie utf-8 a jak nie wyjdzie próbuje z windowsowum cp1250
        linie = f.readlines()
   # CZYTANIE BŁĘDÓW:

for i, linia in enumerate(linie):
        if any(keyword in linia.lower() for keyword in ["stcode", "rejcode", "error", "blad", "rcode"]): #szukam słów kluczowych by wypisać je w liście
                wykluczenia = ["no errors", "when no errors", "error -1"]
                
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

from collections import defaultdict

# Przykładowe dane z błędami dyspensera
linie_dyspensera = [
    "BLAD Dyspensera: 00006434 0000004C 00000000",
    "BLAD Dyspensera: 00006434 0000004C 00000000",
    "BLAD Dyspensera: 00006500 000000FF 00000000",
    "BLAD Dyspensera: 00006434 0000004C 00000000",
    "BLAD Dyspensera: 00006500 000000AA 00000000"
]

# słownik zagnieżdżony: klasa → kod → liczba
bledy_dyspensera = defaultdict(lambda: defaultdict(int))

# wzorzec do wyciągania klasy i kodu
wzorzec_dyspnser = r"BLAD Dyspensera: (\w{8}) (\w{8})"

for linia in linie_dyspensera:
    dopasowanie = re.search(wzorzec_dyspnser, linia)
    if dopasowanie:
        pelna_klasa = dopasowanie.group(1)
        klasa = pelna_klasa[-4:]  # ostatnie 4 znaki
        kod = dopasowanie.group(2)
        bledy_dyspensera[klasa][kod] += 1

import pandas as pd
# Zamiana słownika do DataFrame dla przejrzystości
tabela = []
for klasa, kody in bledy_dyspensera.items():
    for kod, ilosc in kody.items():
        tabela.append((klasa, kod, ilosc))

df = pd.DataFrame(tabela, columns=["Klasa", "Kod błędu", "Ilość wystąpień"])

print("\n📊 Podsumowanie błędów dyspensera:\n")
print(df.to_string(index=False))

print("\n")


