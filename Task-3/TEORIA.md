# Zadanie 3: teoria PSO i działanie algorytmu krok po kroku

Ten dokument wyjaśnia pojęcia teoretyczne, które pojawiają się w zadaniu 3, i pokazuje, co
dokładnie robi optymalizacja rojem cząstek (PSO) z [pso.py](pso.py). Jest kontynuacją teorii do
[zadania 1](../Task-1/TEORIA.md) i [zadania 2](../Task-2/TEORIA.md). Pojęcia dotyczące problemu
(funkcja celu, funkcja kary, optimum lokalne, ILP) i badań (plan czynnikowy, walidacja, test
Manna–Whitneya, wykres pudełkowy) są wyjaśnione tam i tutaj ich nie powtarzamy.

Wszystkie liczby w przykładach policzono na prawdziwych danych z [diet_data.py](diet_data.py)
funkcjami z [pso.py](pso.py). Przykład krok po kroku korzysta z miniaturowego roju (S = 4,
ziarno 42) i parametrów najlepszej konfiguracji z badań.

Spis treści:

1. [Co się zmieniło względem zadań 1–2](#1-co-się-zmieniło-względem-zadań-12)
2. [Inteligencja roju i idea PSO](#2-inteligencja-roju-i-idea-pso)
3. [Elementy PSO](#3-elementy-pso)
4. [PSO dla problemu całkowitoliczbowego](#4-pso-dla-problemu-całkowitoliczbowego)
5. [Parametry PSO](#5-parametry-pso)
6. [Zbieżność roju](#6-zbieżność-roju)
7. [Pojęcia używane w badaniach](#7-pojęcia-używane-w-badaniach)
8. [Algorytm krok po kroku na przykładzie](#8-algorytm-krok-po-kroku-na-przykładzie)
9. [Przebieg całego uruchomienia](#9-przebieg-całego-uruchomienia)
10. [Dlaczego PSO okazało się lepsze](#10-dlaczego-pso-okazało-się-lepsze)

---

## 1. Co się zmieniło względem zadań 1–2

Problem, dane i funkcja celu `f(x) = koszt(x) + 200 · V(x)` są takie same. Zmieniła się metoda:
zamiast algorytmu genetycznego używamy **optymalizacji rojem cząstek** (*Particle Swarm
Optimization*, PSO). Obie metody należą do inteligencji obliczeniowej, przeszukują przestrzeń
rozwiązań zbiorem kandydatów i korzystają z losowości. Różnią się jednak sposobem, w jaki tworzą
nowe rozwiązania:

| AG (zadania 1–2) | PSO (zadanie 3) |
|---|---|
| osobnik, chromosom | cząstka, położenie (i prędkość) |
| populacja | rój |
| pokolenie | iteracja |
| geny całkowite `x_i ∈ {0, …, max_i}` | współrzędne ciągłe `z_i`, zaokrąglane do liczby porcji |
| selekcja: słabe osobniki giną | brak selekcji: każda cząstka „żyje” przez cały przebieg |
| krzyżowanie: potomek dziedziczy geny rodziców | przyciąganie do najlepszego położenia własnego i roju |
| mutacja: losowe zmiany genów | losowe współczynniki `r1`, `r2` i bezwładność |
| elita: najlepszy osobnik przechodzi bez zmian | pamięć: każda cząstka pamięta swoje najlepsze położenie |
| maksymalizacja `F = 1 / (1 + f)` | minimalizacja `f` wprost (selekcja nie jest potrzebna, więc nie trzeba przekształcać `f`) |

Żeby porównanie było uczciwe, obie metody mają **ten sam budżet**: liczba ocen funkcji celu jest
taka sama. Rój `S = 20` cząstek przez 300 iteracji wykonuje `20 · 301 = 6020` ocen, tak samo jak
AG z populacją `N = 20` przez 300 pokoleń.

---

## 2. Inteligencja roju i idea PSO

**Inteligencja roju** (*swarm intelligence*) to dział inteligencji obliczeniowej inspirowany
zachowaniem grup zwierząt: ławic ryb, stad ptaków, kolonii mrówek i pszczół. Pojedynczy osobnik
stosuje proste reguły i zna tylko swoje otoczenie, a mimo to grupa jako całość rozwiązuje trudne
zadania, np. znajduje pożywienie albo najkrótszą drogę.

**PSO** zaproponowali Kennedy i Eberhart w 1995 roku, modelując ruch stada ptaków szukającego
pożywienia. Intuicja:

> Grupa ludzi szuka najniższego punktu terenu we mgle. Każdy pamięta najniższe miejsce, w którym
> sam był, i przez krótkofalówkę słyszy, gdzie jest najniższe miejsce znalezione przez całą grupę.
> W każdym kroku idzie dalej w dotychczasowym kierunku, ale skręca trochę w stronę swojego
> najlepszego miejsca i trochę w stronę najlepszego miejsca grupy.

Trzy elementy tej intuicji to trzy składniki wzoru na prędkość (punkt 3): **bezwładność**
(dotychczasowy kierunek), **składnik poznawczy** (własne doświadczenie) i **składnik społeczny**
(doświadczenie grupy).

Najważniejsze różnice względem AG:

- **brak narodzin i śmierci:** rój ma zawsze te same cząstki, które się poruszają,
- **pamięć:** najlepsze rozwiązania są przechowywane w pamięci cząstek, a nie w populacji,
- **ruch ciągły:** cząstka przesuwa się o wektor prędkości, czyli zmienia wiele współrzędnych naraz
  w jednym, skoordynowanym kierunku.

---

## 3. Elementy PSO

### Cząstka: położenie i prędkość

Cząstka to punkt w przestrzeni rozwiązań, który się porusza. Ma:

- **położenie** `z = (z_1, …, z_21)`: wektor liczb rzeczywistych, który po zaokrągleniu daje
  jadłospis (punkt 4),
- **prędkość** `v = (v_1, …, v_21)`: o ile przesunie się położenie w następnej iteracji.

### Pamięć: pbest i gbest

- **`p` (pbest, *personal best*):** najlepsze położenie, w jakim cząstka była od początku przebiegu.
- **`g` (gbest, *global best*):** najlepsze położenie znalezione przez sąsiedztwo cząstki. W
  topologii globalnej sąsiedztwem jest cały rój, więc `g` to najlepsze rozwiązanie roju. W
  topologii pierścienia `g` to najlepsze z położeń `p` cząstki i jej dwóch sąsiadów (*lbest*,
  *local best*).

Pamięć jest aktualizowana tylko przy poprawie: jeśli nowe położenie jest gorsze, `p` się nie
zmienia. Rozwiązanie zwracane przez algorytm to najlepsze `p` w roju.

### Wzór aktualizacji

W każdej iteracji każda cząstka liczy nową prędkość i przesuwa się:

```
v ← w · v  +  c1 · r1 · (p − z)  +  c2 · r2 · (g − z)
z ← z + v
```

Działania są wykonywane osobno dla każdej współrzędnej, a `r1`, `r2` to liczby losowe z `U(0, 1)`
losowane od nowa dla każdej współrzędnej i każdej cząstki.

| składnik | nazwa | co robi |
|---|---|---|
| `w · v` | bezwładność (*inertia*) | cząstka kontynuuje ruch w dotychczasowym kierunku; `w` określa, ile prędkości „przetrwa” |
| `c1 · r1 · (p − z)` | składnik poznawczy (*cognitive*) | przyciąga cząstkę do jej własnego najlepszego położenia |
| `c2 · r2 · (g − z)` | składnik społeczny (*social*) | przyciąga cząstkę do najlepszego położenia sąsiedztwa |

Przyciąganie jest **proporcjonalne do odległości**: im dalej cząstka jest od `p` i `g`, tym
silniej jest przyciągana. Gdy dobre położenia są blisko siebie, ruchy stają się krótsze. Ta cecha
ma duże znaczenie dla wyników (punkt 10).

### Przykład liczbowy dla jednej współrzędnej

Niech `z = 1,0`, `v = 0,5`, `p = 2,0`, `g = 0,0`, `w = 1,0`, `c1 = 2,5`, `c2 = 0,5`, a losowanie
dało `r1 = 0,4`, `r2 = 0,6`:

```
v ← 1,0 · 0,5  +  2,5 · 0,4 · (2,0 − 1,0)  +  0,5 · 0,6 · (0,0 − 1,0)
  =     0,5     +          1,0             −          0,3              = 1,2
z ← 1,0 + 1,2 = 2,2
```

Cząstka poruszała się w górę (bezwładność), składnik poznawczy pchnął ją mocniej w górę (do `p`),
a społeczny lekko w dół (do `g`). Nowe położenie 2,2 przekroczyło nawet `p` – takie „przestrzelenie”
jest w PSO normalne i pozwala badać okolicę dobrych rozwiązań z obu stron.

---

## 4. PSO dla problemu całkowitoliczbowego

PSO zaprojektowano dla przestrzeni ciągłych, a jadłospis składa się z całych porcji. Trzeba więc
określić, jak położenie ciągłe zamienić na jadłospis.

### Dekodowanie przez zaokrąglenie

Położenie `z_i` należy do przedziału `[−0,5; max_i + 0,5]`, a jadłospis to `x_i = round(z_i)`.
Dla jabłka (`max = 3`):

```
z:   −0,5 ──── 0,5 ──── 1,5 ──── 2,5 ──── 3,5
x:        0         1         2         3
```

Każda liczba porcji dostaje przedział o długości 1. Gdyby położenia leżały w `[0; max_i]`, wartości
skrajne (0 i `max_i`) miałyby przedziały o połowę krótsze i losowa inicjalizacja rzadziej by je
wybierała.

Funkcja celu jest liczona dla zaokrąglonego jadłospisu, a ruch odbywa się w przestrzeni ciągłej.
Cząstka może więc stopniowo przesuwać się w stronę progu zaokrąglenia przez kilka iteracji, zanim
liczba porcji faktycznie się zmieni.

### Płaskowyże

Funkcja celu widziana przez cząstkę jest **schodkowa**: jest stała w każdej „kostce” o boku 1
wokół punktu całkowitego. Ruch o 0,3 może w ogóle nie zmienić jadłospisu. Przykład z punktu 8:
położenie orzechów cząstki 2 przesuwa się z 2,17 na 2,47, ale jadłospis nadal ma 2 porcje.

Konsekwencja: jeśli prędkości cząstek staną się małe (rój się zbiegnie), cząstki będą wielokrotnie
oceniać te same jadłospisy. Takie oceny niczego nie wnoszą, a zużywają budżet. W przestrzeni
ciągłej ten problem nie występuje, bo każdy, nawet mały ruch daje nowe rozwiązanie.

### Granice

Ruch może wyprowadzić współrzędną poza zakres. Zastosowano **ściany pochłaniające**: współrzędna
zatrzymuje się na granicy, a jej prędkość jest zerowana. Inne spotykane możliwości to odbicie
(prędkość zmienia znak) albo losowe nowe położenie.

### Ograniczenie prędkości v_max

Prędkość każdej współrzędnej jest obcinana do `±v_max · (max_i + 1)`. `v_max = 1,0` oznacza, że w
jednym kroku cząstka może przelecieć przez cały zakres zmiennej, a `v_max = 0,1` – tylko o 10%
zakresu. Ograniczenie zapobiega „wybuchowi” prędkości, gdy rój jest niestabilny (punkt 6).

---

## 5. Parametry PSO

### Bezwładność w

- **Duże `w`** (0,9–1,1): cząstka długo utrzymuje kierunek ruchu, przelatuje duże odległości.
  Przewaga **eksploracji** (szerokiego przeszukiwania).
- **Małe `w`** (0,4–0,6): prędkość szybko wygasa, cząstka krąży blisko `p` i `g`. Przewaga
  **eksploatacji** (dopracowywania znalezionych rozwiązań).
- **Liniowo malejące `w`** (np. 0,9 → 0,4, Shi i Eberhart): na początku eksploracja, pod koniec
  eksploatacja. Bardzo popularny schemat dla problemów ciągłych.

### Współczynniki c1 i c2

- **`c1`** (poznawczy) określa, jak silnie cząstka wraca do własnego najlepszego położenia.
- **`c2`** (społeczny) określa, jak silnie cząstka podąża za najlepszym położeniem sąsiedztwa.

Przypadki skrajne:

- **`c2 = 0`:** cząstki nie wymieniają informacji. Rój to `S` niezależnych przeszukiwań.
- **`c1 = 0`:** cały rój goni jeden punkt `g`, co grozi szybkim zapadnięciem się w optimum
  lokalnym.

W badaniach sprawdzono pary symetryczne (1; 1), (1,494; 1,494), (2; 2) i niesymetryczne
(0,5; 2,5), (2,5; 0,5), (3; 0).

### Topologia

Topologia określa, kogo cząstka „słyszy”:

- **globalna (gbest):** każda cząstka zna najlepsze rozwiązanie całego roju. Informacja rozchodzi
  się natychmiast, rój szybko się zbiega.
- **pierścień (lbest):** cząstka `i` zna tylko siebie i sąsiadów `i − 1`, `i + 1`. Informacja
  przechodzi o jedną cząstkę na iterację, więc różne części roju mogą dłużej badać różne obszary.

### Rozmiar roju

Przy stałym budżecie większy rój oznacza mniej iteracji: `S = 10` → 601 iteracji, `S = 20` → 300,
`S = 40` → 149. Mały rój ma mało różnorodności, a duży mało czasu na dopracowanie rozwiązania.

---

## 6. Zbieżność roju

### Model jednej cząstki

Załóżmy, że `p` i `g` się nie zmieniają (tzw. stagnacja). Wtedy ruch jednej współrzędnej cząstki
opisuje równanie

```
z(t+1) = (1 + w − φ) · z(t) − w · z(t−1) + φ · P,     φ = c1 · r1 + c2 · r2
```

gdzie `P` to ważona średnia `p` i `g`. To równanie drugiego rzędu z losowym współczynnikiem `φ`.
W zależności od `w`, `c1` i `c2` cząstka:

- **zbiega się:** drga wokół `P` z coraz mniejszą amplitudą i w końcu się zatrzymuje,
- **nie zbiega się:** drga z amplitudą stałą lub rosnącą. W praktyce ruch ograniczają wtedy tylko
  `v_max` i granice przestrzeni.

### Obszar zbieżności

Poli (2009) wyznaczył warunek, przy którym zbiega się zarówno średnie położenie cząstki, jak i
jego rozrzut (zbieżność drugiego rzędu):

```
|w| < 1   oraz   c1 + c2 < 24 · (1 − w²) / (7 − 5w)
```

Granica dla wartości `w` z badań:

| `w` | maksymalne `c1 + c2` | rój zbieżny dla par z badań |
|---|---|---|
| 0,4 | 4,03 | wszystkie (suma ≤ 4) |
| 0,6 | 3,84 | wszystkie poza (2; 2) |
| 0,729 | 3,35 | wszystkie poza (2; 2) |
| 0,9 | 1,82 | żadna (sumy 2–4) |
| 1,0 i 1,1 | brak (`w ≥ 1`) | żadna |
| 0,9 → 0,4 | 4,03 (na końcu przebiegu) | wszystkie |

Na wykresie [inertia_coefficients.png](results/inertia_coefficients.png) pola roju zbieżnego są
zakreskowane. Z 1008 konfiguracji 528 jest zbieżnych, a 480 niezbieżnych.

### Standardowe PSO

W literaturze często poleca się `w = 0,729`, `c1 = c2 = 1,49445` (ustawienie wynikające ze
współczynnika zawężenia Clerca i Kennedy'ego). Suma 2,99 < 3,35, więc rój jest zbieżny, ale blisko
granicy. Dla problemów ciągłych to dobry kompromis: cząstki najpierw szeroko przeszukują przestrzeń,
a potem precyzyjnie zbliżają się do optimum. W badaniach jest to konfiguracja „PSO standardowe”.

### Co oznacza zbieżność w problemie dyskretnym

W problemie ciągłym zbieżność jest pożądana: cząstki zbliżają się do optimum z dowolną
dokładnością. W problemie całkowitoliczbowym zbieżny rój po kilkudziesięciu iteracjach ma prędkości
mniejsze niż 0,5, więc cząstki **przestają zmieniać jadłospis** (płaskowyże z punktu 4). Pomiar:
standardowe PSO pod koniec przebiegu ocenia nowe rozwiązania tylko w 20% przypadków, a w 80%
ponownie te same jadłospisy. Najlepsza konfiguracja z badań (`w = 1,0`) jest **niezbieżna**: jej
cząstki nigdy się nie zatrzymują, a ruch ograniczają `v_max` i ściany.

---

## 7. Pojęcia używane w badaniach

Plan czynnikowy, „średnia danej wartości” i „najlepsza konfiguracja”, błąd standardowy,
przekleństwo zwycięzcy, walidacja, test Manna–Whitneya i wykres pudełkowy są wyjaśnione w
[teorii do zadania 2](../Task-2/TEORIA.md#6-pojęcia-używane-w-badaniach). Doszły nowe pojęcia
związane z porównaniem dwóch różnych metod.

### Uczciwe porównanie dwóch metod

Żeby stwierdzić, która metoda jest lepsza, trzeba porównać je w tych samych warunkach:

- **ten sam budżet:** liczba ocen funkcji celu, a nie liczba iteracji (iteracja PSO i pokolenie AG
  to różne rzeczy, ale każde ocenia tyle samo rozwiązań),
- **te same ziarna:** walidacja PSO i AG korzysta z tych samych ziaren 1000–1099,
- **podobny wysiłek strojenia:** AG dostroiliśmy w zadaniu 2 (2592 konfiguracje), a PSO w zadaniu 3
  (1008 konfiguracji). Porównujemy najlepsze konfiguracje obu metod,
- **różne budżety:** metoda szybsza na początku nie musi być lepsza na końcu, dlatego w etapie 3
  porównujemy budżety od 1500 do 24 000 ocen.

### Odległość Hamminga i różnorodność

**Odległość Hamminga** dwóch jadłospisów to liczba produktów, których liczba porcji się różni. Np.
`[2, 0, 1]` i `[2, 1, 0]` mają odległość 2.

**Różnorodność** populacji (roju) mierzymy jako średnią odległość Hamminga między dwoma
rozwiązaniami. Losowa populacja ma ok. 14 (z 21 produktów), a populacja złożona z jednakowych
rozwiązań ma 0.

### Nowe rozwiązania

Odsetek ocen w danej iteracji (pokoleniu), których jadłospisu **nie było** w poprzedniej populacji.
Mierzy, ile budżetu idzie na badanie nowych rozwiązań, a ile na ponowne ocenianie znanych. W AG
z elitą ten odsetek nie może przekroczyć 95%, bo elita jest kopiowana bez zmian.

### Długość kroku

Odległość Hamminga nowego rozwiązania od **najbliższego** rozwiązania poprzedniej populacji
(liczona tylko dla nowych rozwiązań). Mierzy, jak daleko metoda „sięga” od tego, co już zna:
krok 1 to zmiana jednego produktu, krok 5 to zmiana pięciu produktów naraz.

### Twierdzenie „nie ma darmowego obiadu”

Twierdzenie Wolperta i Macready'ego (1997, *No Free Lunch*) mówi, że uśredniona po **wszystkich**
możliwych problemach skuteczność każdych dwóch metod przeszukiwania jest taka sama. Nie istnieje
więc metoda najlepsza dla każdego problemu. Wynik „PSO jest lepsze od AG” dotyczy tego problemu,
tego kodowania, tych operatorów i tego budżetu, a nie metod w ogóle.

---

## 8. Algorytm krok po kroku na przykładzie

### Pseudokod

```
wczytaj dane, ustaw konfigurację (S, T, w, c1, c2, topologia, v_max, seed)
z ← S losowych położeń, v ← S losowych prędkości         # krok 1: inicjalizacja
x ← round(z); oceń f(x)                                    # krok 1: dekodowanie i ocena
p ← z (pamięć każdej cząstki)                              # krok 2: pamięć

dla t = 0, 1, …, T:
    zaktualizuj najlepsze rozwiązanie, zapisz statystyki
    jeśli t = T: zakończ
    g ← najlepsze p w sąsiedztwie każdej cząstki           # krok 2
    v ← w·v + c1·r1·(p − z) + c2·r2·(g − z)                # krok 3: nowa prędkość
    v ← obetnij do ±v_max
    z ← z + v; na granicy: z ← granica, v ← 0              # krok 4: ruch
    x ← round(z); oceń f(x)                                # krok 5: ocena
    jeśli f(x) < f(p): p ← z                               # krok 5: aktualizacja pamięci

zwróć najlepsze p
```

Odpowiada to funkcji `run_pso` w [pso.py](pso.py). Przykład: rój `S = 4`, ziarno 42, parametry
najlepszej konfiguracji z badań: `w = 1,0`, `c1 = 2,5`, `c2 = 0,5`, topologia globalna,
`v_max = 1,0`, czyli `|v_i| ≤ max_i + 1` (np. 3 dla płatków, 4 dla chleba).

### Krok 1: inicjalizacja i ocena

Położenia i prędkości są losowane równomiernie. Pierwsze współrzędne cząstki 0:

```
z = [ 1,82   1,26   2,08   1,59  −0,12  …   2,53 ]
x = [   2      1      2      2      0   …     3  ]      (oliwa: 2,53 ∈ [2,5; 3,5) → 3)
```

Cały rój po dekodowaniu:

| cząstka | jadłospis `x` | koszt [zł] | V | f [zł] |
|---|---|---|---|---|
| 0 | `[2, 1, 2, 2, 0, 2, 2, 2, 0, 1, 0, 1, 1, 2, 1, 0, 1, 0, 2, 2, 3]` | 32,80 | 2,972 | 627,26 |
| 1 | `[1, 3, 2, 2, 0, 1, 0, 0, 2, 2, 1, 0, 1, 1, 0, 0, 1, 0, 2, 1, 3]` | 29,70 | 1,815 | 392,70 |
| 2 | `[2, 1, 2, 2, 1, 0, 2, 0, 0, 0, 1, 1, 2, 2, 1, 2, 0, 0, 2, 1, 2]` | 29,30 | 2,405 | 510,29 |
| 3 | `[2, 2, 1, 1, 1, 0, 1, 0, 1, 2, 0, 0, 0, 0, 1, 2, 2, 1, 1, 3, 0]` | 20,80 | 1,077 | **236,18** |

Wszystkie losowe jadłospisy są za duże (średnio ok. 1 porcja każdego z 21 produktów) i mocno
łamią ograniczenia, dlatego `f` jest rzędu setek złotych.

### Krok 2: pamięć

Na początku `p = z` dla każdej cząstki. Najlepsza jest cząstka 3 (`f = 236,18 zł`), więc w
topologii globalnej `g` to położenie cząstki 3 dla wszystkich cząstek.

### Krok 3: nowa prędkość cząstki 0

Wybrane współrzędne (pełne obliczenie obejmuje wszystkie 21):

| produkt | `z` | `v` | `g` | `w·v` | `c1·r1·(p − z)` | `c2·r2·(g − z)` | nowe `v` |
|---|---|---|---|---|---|---|---|
| płatki owsiane | 1,82 | −2,86 | 1,79 | −2,86 | 0 | −0,01 | −2,87 |
| makaron | 1,59 | −0,23 | 1,18 | −0,23 | 0 | −0,15 | −0,38 |
| twaróg | 1,86 | 1,18 | 0,14 | 1,18 | 0 | −0,51 | 0,67 |
| brokuł | 1,43 | −0,83 | 0,34 | −0,83 | 0 | −0,50 | −1,33 |
| masło orzechowe | 1,98 | −1,40 | 0,72 | −1,40 | 0 | −0,04 | −1,44 |
| ser żółty | 2,03 | 3,75 | 2,76 | 3,75 | 0 | 0,06 | 3,82 |

Obserwacje:

- **Składnik poznawczy jest zerowy**, bo w pierwszej iteracji `p = z`.
- Składnik społeczny ciągnie każdą współrzędną w stronę cząstki 3. Np. dla makaronu:
  `0,5 · 0,75 · (1,18 − 1,59) = −0,15` (wylosowano `r2 = 0,75`).
- W pierwszej iteracji **dominuje bezwładność**, bo prędkości początkowe są losowe i duże. Ruch jest
  więc w dużej mierze przypadkowy.
- Żadna prędkość nie przekracza `v_max` (np. ser: 3,82 ≤ 4).

### Krok 4: ruch, granice i dekodowanie

| produkt | `z + v` | po granicy | nowe `x` | zmiana |
|---|---|---|---|---|
| płatki owsiane | −1,05 | −0,50 (ściana, `v ← 0`) | 0 | 2 → 0 |
| makaron | 1,21 | 1,21 | 1 | 2 → 1 |
| twaróg | 2,53 | 2,50 (ściana, `v ← 0`) | 2 | bez zmian |
| brokuł | 0,10 | 0,10 | 0 | 1 → 0 |
| masło orzechowe | 0,54 | 0,54 | 1 | 2 → 1 |
| ser żółty | 5,84 | 3,50 (ściana, `v ← 0`) | 3 | 2 → 3 |

W całym wektorze cząstki 0 **13 z 21 współrzędnych uderzyło w ścianę**, a zmieniło się **12
produktów naraz**. Taki duży skok jest typowy dla początku przebiegu z `v_max = 1,0`.

### Krok 5: ocena i aktualizacja pamięci

| cząstka | f przed [zł] | f po [zł] | pamięć `p` |
|---|---|---|---|
| 0 | 627,26 | 242,00 | poprawa → nowe `p` |
| 1 | 392,70 | 377,05 | poprawa → nowe `p` |
| 2 | 510,29 | **101,90** | poprawa → nowe `p`, **nowe `g`** |
| 3 | 236,18 | 573,76 | **pogorszenie** → `p` bez zmian (236,18) |

Cząstka 3 była najlepsza, a mimo to odleciała w gorsze miejsce. W PSO nie ma elity, która trzymałaby
najlepsze rozwiązanie w roju. Jest ono przechowywane tylko w **pamięci** (`p` cząstki 3), dlatego
nie ginie. To zasadnicza różnica względem AG: **bieżące położenia mogą być dowolnie złe, a postęp
i tak nie jest tracony**.

### Kolejne iteracje

| po iteracji | f cząstek [zł] | pamięć `f(p)` [zł] | `g` |
|---|---|---|---|
| 1 | 242,00; 377,05; 101,90; 573,76 | 242,00; 377,05; 101,90; 236,18 | cząstka 2 (101,90) |
| 2 | 106,25; 193,96; 74,54; 136,06 | 106,25; 193,96; 74,54; 136,06 | cząstka 2 (74,54) |
| 3 | 58,12; 198,71; 137,34; 34,50 | 58,12; 193,96; 74,54; 34,50 | cząstka 3 (34,50) |
| 4 | 66,90; 428,16; 161,30; 133,87 | 58,12; 193,96; 74,54; 34,50 | cząstka 3 (34,50) |

Po trzech iteracjach cząstka 2 jest gorsza od swojej pamięci (137,34 wobec 74,54 zł), więc w
czwartej iteracji **działa składnik poznawczy**. Wybrane współrzędne cząstki 2:

| produkt | `z` (x) | `v` | `p` | `g` | `w·v` | poznawczy | społeczny | nowe `v` | nowe `z` (x) |
|---|---|---|---|---|---|---|---|---|---|
| płatki owsiane | −0,50 (0) | 0,00 | −0,28 | 0,61 | 0,00 | 0,44 | 0,40 | 0,84 | 0,34 (0) |
| mleko | 2,24 (2) | 0,71 | 1,53 | −0,50 | 0,71 | −0,06 | −0,95 | −0,30 | 1,94 (2) |
| jabłko | 1,54 (2) | −0,08 | 1,62 | 0,36 | −0,08 | 0,10 | −0,35 | −0,32 | 1,22 (**1**) |
| orzechy włoskie | 2,17 (2) | 0,77 | 1,39 | 1,33 | 0,77 | −0,10 | −0,38 | 0,30 | 2,47 (2) |
| masło orzechowe | 0,75 (1) | −0,25 | 1,00 | 2,50 | −0,25 | 0,07 | 0,77 | 0,59 | 1,34 (1) |

Obserwacje:

- Pamięć cząstki 2 różni się od jej bieżącego jadłospisu tylko orzechami (1 zamiast 2 porcji).
  Składnik poznawczy ciągnie orzechy w dół, ale bezwładność (0,77) jest silniejsza i położenie
  rośnie do 2,47. To **przestrzelenie**: cząstka nie wraca od razu do `p`, tylko przelatuje obok
  i bada okolicę.
- Położenie orzechów zmienia się o 0,30, ale jadłospis nadal ma 2 porcje (**płaskowyż**).
- Płatki stały na ścianie z prędkością 0. Oba składniki przyciągania wyprowadzają je ze ściany.
- W całym wektorze zmieniły się 3 produkty (ryż 0 → 1, pomidor 1 → 0, jabłko 2 → 1), a `f` wzrosło
  do 161,30 zł. Pamięć nadal trzyma 74,54 zł.

---

## 9. Przebieg całego uruchomienia

To samo ziarno (1000), budżet 6020 ocen, dwie konfiguracje PSO:

- **najlepsze PSO:** `S = 20`, `w = 1,0`, `c = (2,5; 0,5)`, topologia globalna, `v_max = 1,0`,
- **standardowe PSO:** `S = 20`, `w = 0,729`, `c = (1,49445; 1,49445)`, topologia globalna,
  `v_max = 1,0`.

Wartości `f` w złotówkach, „zmienione” to odsetek cząstek, których jadłospis zmienił się w danej
iteracji, „różnorodność” to średnia odległość Hamminga w roju:

| iteracja | najlepsze PSO: najlepsza w roju | średnia roju | najlepsze dotąd | zmienione | różnorodność | standardowe: najlepsze dotąd | zmienione | różnorodność |
|---|---|---|---|---|---|---|---|---|
| 0 | 33,30 | 266,71 | 33,30 | — | 14,3 | 33,30 | — | 14,3 |
| 1 | 33,43 | 269,09 | 33,30 | 100% | 13,1 | 22,20 | 100% | 13,1 |
| 5 | 27,12 | 133,75 | 27,12 | 100% | 12,3 | 14,20 | 100% | 9,6 |
| 10 | 15,40 | 111,76 | 15,40 | 100% | 10,9 | 12,30 | 100% | 7,6 |
| 25 | 14,04 | 80,96 | 13,10 | 100% | 10,6 | 12,30 | 95% | 4,6 |
| 50 | 12,60 | 56,64 | 11,80 | 95% | 10,1 | 11,50 | 75% | 3,1 |
| 100 | 17,80 | 96,20 | 8,90 | 100% | 9,4 | 10,40 | 75% | 2,0 |
| 150 | 11,62 | 82,84 | 8,60 | 95% | 7,0 | 10,40 | 35% | 0,9 |
| 200 | 7,70 | 56,31 | **7,70** | 95% | 6,0 | 10,40 | 40% | 0,9 |
| 300 | 7,70 | 33,93 | 7,70 | 80% | 3,9 | 10,40 | 20% | 0,5 |

Co widać:

1. **Standardowe PSO jest szybsze na początku** (12,30 zł po 10 iteracjach wobec 15,40 zł), ale
   **utknęło w iteracji 87** na 10,40 zł. Różnorodność spadła do 0,5 produktu, a pod koniec tylko
   20% cząstek zmienia jadłospis. Rój się zbiegł i resztę budżetu zużywa na powtórne oceny.
2. **Najlepsze PSO poprawia się przez cały przebieg:** 8,90 zł (iteracja 93), 8,60 (117), 8,10
   (177) i **optimum 7,70 zł w iteracji 197**. Do iteracji 200 prawie wszystkie cząstki zmieniają
   jadłospis w każdym kroku.
3. **Bieżące położenia najlepszego PSO są przeważnie złe.** Średnia roju to 34–270 zł, a w
   iteracji 100 najlepsza cząstka w roju ma 17,80 zł, choć najlepsze znalezione rozwiązanie to
   8,90 zł. Cząstki stale latają także przez słabe obszary, a dobre rozwiązania przechowuje pamięć.
4. **Różnorodność najlepszego PSO maleje powoli** (14,3 → 3,9), bo położenia `p` stopniowo
   skupiają się wokół dobrych rozwiązań, a razem z nimi skracają się ruchy cząstek.

Dla porównania AG z zadania 2 na tym samym ziarnie kończy na 8,50 zł (od pokolenia 34 do 217 stał
na 9,50 zł). Pojedyncze uruchomienie nie przesądza jednak o niczym: na ziarnie 1007 jest odwrotnie,
AG znajduje optimum w pokoleniu 68, a najlepsze PSO kończy na 8,50 zł. O wyższości metody decyduje
statystyka ze 100 uruchomień (punkt 10).

---

## 10. Dlaczego PSO okazało się lepsze

### Odpowiedź

Przy budżecie ok. 6000 ocen (walidacja, 100 uruchomień):

| | najlepsze PSO | AG zad. 2 |
|---|---|---|
| średnia f | **8,25 zł** | 8,54 zł |
| znalezione optimum | **48%** | 6% |
| wynik dokładnie 8,10 zł (optimum lokalne) | 6% | **46%** |

Różnica jest istotna statystycznie (test Manna–Whitneya, p = 0,0003). Przy 24 000 ocen PSO trafia w
optimum w 80% uruchomień, a AG w 8%. Poniżej pięć przyczyn, każda poparta pomiarem z etapu 4.

### 1. Brak selekcji: cząstka może przejść przez gorsze rozwiązania

Typowy wynik AG to optimum lokalne za 8,10 zł, np.:

```
optimum (7,70 zł):          ryż 0, makaron 2, mleko 0, oliwa 2
optimum lokalne (8,10 zł):  ryż 1, makaron 1, mleko 1, oliwa 1   (reszta jadłospisu taka sama)
```

Do optimum trzeba zmienić **cztery produkty naraz**. Sprawdzono wszystkie 14 jadłospisów
pośrednich (zmiana 1, 2 lub 3 z tych czterech produktów) i **każdy jest gorszy** od 8,10 zł:

| zmienione produkty | f [zł] |
|---|---|
| tylko ryż / tylko makaron / tylko mleko / tylko oliwa | 59,81 / 47,09 / 31,37 / 8,50 |
| ryż i makaron | 8,20 |
| ryż, makaron i oliwa | 8,60 |
| pozostałe kombinacje 2–3 produktów | 17,69–105,56 |
| wszystkie cztery | **7,70** (optimum) |

Żadna zmiana jednego produktu (w całym jadłospisie) nie poprawia wyniku 8,10 zł. Najłagodniejsza
droga do optimum prowadzi przez 8,20 i 8,60 zł. W AG z elitą takie gorsze rozwiązania pośrednie
zwykle przegrywają turnieje z osobnikiem za 8,10 zł i jego kopiami, więc droga przez nie rzadko
zostaje dokończona.

W PSO nie ma selekcji. Cząstka porusza się zgodnie z prędkością **niezależnie od tego, czy bieżący
jadłospis jest dobry**, a dobre rozwiązanie i tak pozostaje w pamięci `p`. Cząstka może więc przez
kilka iteracji przelatywać przez gorsze jadłospisy i wylądować w lepszym obszarze. Pomiar: tylko
6% uruchomień najlepszego PSO kończy się na 8,10 zł, wobec 46% w AG.

### 2. Rój niezbieżny nie marnuje ocen

Z powodu płaskowyży (punkt 4) zbieżny rój pod koniec ocenia te same jadłospisy:

| metoda | nowe rozwiązania po 1500 ocenach | po 6000 ocenach |
|---|---|---|
| najlepsze PSO (`w = 1,0`, niezbieżne) | 99% | 91% |
| AG zad. 2 | 74% | 72% |
| AG zad. 1 | 55% | 54% |
| standardowe PSO (zbieżne) | 41% | 20% |

To wyjaśnia, dlaczego w siatce rój niezbieżny jest średnio dużo lepszy od zbieżnego (10,31 wobec
14,42 zł) i dlaczego najlepsze konfiguracje mają `w ≥ 0,9`, czyli więcej, niż zaleca się dla
problemów ciągłych. Przy `w = 1,0` prędkość nie wygasa, ale nie rośnie też bez końca, bo ogranicza
ją `v_max`, a ściany zerują ją przy uderzeniu w granicę.

### 3. Samoczynne przejście od eksploracji do eksploatacji

Składniki przyciągania są proporcjonalne do odległości od `p` i `g`. Gdy pamięci cząstek skupiają
się wokół dobrych rozwiązań, ruchy samoczynnie się skracają:

| metoda | długość kroku po 500 ocenach | 1500 | 3000 | 6000 |
|---|---|---|---|---|
| najlepsze PSO | 5,5 produktu | 4,7 | 3,7 | 2,6 |
| AG zad. 2 | 4,0 | 3,6 | 3,5 | 3,3 |

PSO zaczyna od dalekich skoków (eksploracja), a kończy na krokach zmieniających 2–3 produkty
naraz, czyli dokładnie takich, jakich potrzeba do wyjścia z optimów lokalnych blisko optimum
(punkt 1). AG ma stały rozmiar zmian, bo zależy on tylko od ustalonego `p_m`. Te same kroki są w
AG za małe na początku i nie dość ukierunkowane na końcu.

Ta sama cecha jest jednak **kosztem PSO na początku**: dalekie skoki przez słabe obszary sprawiają,
że przy małym budżecie AG jest lepszy. Średnie krzywe przecinają się przy ok. **3600 ocenach**:

| oceny | 1000 | 2000 | 3000 | 4000 | 5000 | 6000 |
|---|---|---|---|---|---|---|
| najlepsze PSO [zł] | 11,16 | 9,88 | 9,10 | **8,67** | **8,44** | **8,25** |
| AG zad. 2 [zł] | **10,10** | **9,17** | **8,93** | 8,78 | 8,65 | 8,54 |

### 4. Silna pamięć indywidualna, słaba współpraca

Najlepsze konfiguracje mają `c1 = 2,5` i `c2 = 0,5` (15 z 20 najlepszych konfiguracji etapu 1).
Każda cząstka bada głównie okolice **własnego** najlepszego położenia, więc rój prowadzi
jednocześnie 20 częściowo niezależnych przeszukiwań w różnych obszarach. Słaby składnik społeczny
powoli przyciąga je do najlepszego rozwiązania roju.

Oba skrajne warianty są gorsze:

- **`c2 = 0` (brak współpracy):** walidacja 11,11 zł. Cząstki nie dowiadują się o dobrych obszarach
  znalezionych przez inne.
- **`c = (0,5; 2,5)` (dominuje współpraca):** walidacja 8,80 zł. Cały rój goni jeden punkt i
  szybciej traci różnorodność.

W AG odpowiednikiem pamięci jest tylko jeden osobnik elitarny. Pozostali osobnicy są w każdym
pokoleniu zastępowani potomkami, więc dobre rozwiązanie, które nie jest najlepsze w populacji,
łatwo ginie. W PSO każda z 20 cząstek ma własną pamięć, która nigdy nie zostaje utracona.

### 5. Ruch ciągły pasuje do struktury problemu

- Koszt i składniki odżywcze są **liniowe** względem liczby porcji (to problem programowania
  liniowego całkowitoliczbowego). Kierunek, który poprawia jadłospis, pozostaje dobry przez kilka
  kroków, więc bezwładność („idź dalej w tym samym kierunku”) ma sens.
- Kodowanie zachowuje **porządek** wartości: 1 porcja leży między 0 i 2. Cząstka zmienia liczbę
  porcji stopniowo i w kierunku dobrych rozwiązań. Mutacja przez reset w AG losuje wartość bez
  związku z poprzednią, a inwersja przenosi wartości między różnymi produktami.
- Ruch cząstki zmienia **wiele produktów naraz w skoordynowany sposób** (wszystkie w stronę `p`
  i `g`), co przypomina krzyżowanie z dobrym rozwiązaniem, ale z możliwością przestrzelenia.

### Kiedy AG jest lepszy

- **Mały budżet** (poniżej ok. 3600 ocen): AG z elitą jest bardziej zachłanny i szybciej znajduje
  dobre rozwiązania.
- **Brak strojenia:** przeciętna konfiguracja PSO z siatki daje 12,46 zł, a AG z zadania 2 ok.
  10,07 zł. Standardowe PSO z literatury (11,08 zł) jest gorsze nawet od AG z zadania 1
  (10,09 zł). Dla odniesienia czyste losowanie 6020 jadłospisów daje średnio 13,15 zł, a 271 z
  1008 konfiguracji PSO jest od niego gorszych. AG jest dużo mniej wrażliwy na parametry.

Zgodnie z twierdzeniem „nie ma darmowego obiadu” (punkt 7) wynik dotyczy tego problemu i tej
implementacji. Dla problemu ciągłego albo z innym kodowaniem kolejność metod mogłaby być inna.
