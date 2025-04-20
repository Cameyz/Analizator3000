import os

# 📂 Ścieżka do folderu z plikami – możesz zmienić na swoją
folder = r"D:\Projekty\Python\Analizator3000\Dzienniki"

# ✅ Zapytaj użytkownika o dane
dodatek = input("🔤 Jaki ciąg znaków chcesz dodać do nazw plików? ")
pozycja = input("📍 Gdzie dodać ciąg? Wpisz 'start' (na początku) lub 'end' (na końcu): ").strip().lower()

# 🧠 Obsługa przypadków start / end
if pozycja not in ['start', 'end']:
    print("❌ Nieprawidłowa opcja. Wpisz 'start' albo 'end'.")
    exit()

# 🔁 Iteracja po plikach w folderze
for nazwa_pliku in os.listdir(folder):
    pelna_sciezka = os.path.join(folder, nazwa_pliku)

    if os.path.isfile(pelna_sciezka):
        nazwa, rozszerzenie = os.path.splitext(nazwa_pliku)

        if pozycja == "start":
            nowa_nazwa = f"{dodatek}{nazwa_pliku}"
        else:  # pozycja == "end"
            nowa_nazwa = f"{nazwa}{dodatek}{rozszerzenie}"

        nowa_sciezka = os.path.join(folder, nowa_nazwa)

        os.rename(pelna_sciezka, nowa_sciezka)
        print(f"✅ {nazwa_pliku} ➜ {nowa_nazwa}")
