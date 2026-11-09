# Zadanie 2: teoria i działanie algorytmu krok po kroku

Ten dokument wyjaśnia pojęcia teoretyczne, które pojawiają się w zadaniu 2, i pokazuje, co
dokładnie robią nowe operatory z [ga.py](ga.py). Jest kontynuacją
[teorii do zadania 1](../Task-1/TEORIA.md). Podstawowe pojęcia (chromosom, gen, funkcja celu,
funkcja kary, przystosowanie, selekcja turniejowa, krzyżowanie jednopunktowe, mutacja przez reset,
optimum lokalne, ILP) są wyjaśnione tam i tutaj ich nie powtarzamy.

Wszystkie liczby w przykładach policzono na prawdziwych danych z [diet_data.py](diet_data.py)
funkcjami z [ga.py](ga.py). Przykłady korzystają z tej samej miniaturowej populacji (N = 4,
ziarno 42) co w zadaniu 1, więc można je porównać krok po kroku.

Spis treści:

1. [Co się zmieniło względem zadania 1](#1-co-się-zmieniło-względem-zadania-1)
2. [Elitaryzm](#2-elitaryzm)
3. [Metody selekcji](#3-metody-selekcji)
4. [Metody krzyżowania](#4-metody-krzyżowania)
5. [Operatory mutacji](#5-operatory-mutacji)
6. [Pojęcia używane w badaniach](#6-pojęcia-używane-w-badaniach)
7. [Algorytm krok po kroku na przykładzie](#7-algorytm-krok-po-kroku-na-przykładzie)
8. [Przebieg całego uruchomienia](#8-przebieg-całego-uruchomienia)
9. [Dlaczego zwycięska kombinacja działa](#9-dlaczego-zwycięska-kombinacja-działa)

---

## 1. Co się zmieniło względem zadania 1

Problem, chromosom, funkcja celu `f(x) = koszt(x) + 200 · V(x)` i przystosowanie
`F(x) = 1 / (1 + f(x))` są takie same. Zmienił się tylko algorytm: każdy jego element można teraz
wymienić na inny wariant.

| element AG | zadanie 1 | zadanie 2 (do wyboru) |
|---|---|---|
| sukcesja | pokoleniowa | pokoleniowa **z elitaryzmem** (`e` najlepszych przeżywa) |
| selekcja | turniejowa | turniejowa, **ruletkowa**, **rankingowa** |
| krzyżowanie | jednopunktowe | jednopunktowe, **dwupunktowe**, **równomierne** |
| mutacja | reset | reset, **inwersja**, **±1 (creep)** |

**Operator** to wymienny „klocek” algorytmu. Ogólny schemat AG (selekcja → krzyżowanie → mutacja
→ sukcesja) się nie zmienia, zmieniają się tylko klocki. Dzięki temu można sprawdzić, które klocki
najlepiej pasują do danego problemu, i właśnie to jest celem zadania 2.

---

## 2. Elitaryzm

### Definicja

**Elitaryzm** (selekcja elitarna, strategia elitarna) polega na tym, że `e` najlepszych osobników
bieżącej populacji (**elita**) przechodzi do następnego pokolenia **bez żadnych zmian**: nie są
krzyżowani ani mutowani. Pozostałe `N − e` miejsc zajmują potomkowie utworzeni zwykłą drogą
(selekcja, krzyżowanie, mutacja).

```
pokolenie t:     [ najlepszy | 2. | 3. | ... | najgorszy ]
                       │
                       │ kopia bez zmian (e = 1)
                       ▼
pokolenie t+1:   [ najlepszy | potomek 1 | potomek 2 | ... | potomek N−1 ]
```

Parametr `e` to **rozmiar elity**. `e = 0` oznacza brak elitaryzmu, czyli zwykłą sukcesję
pokoleniową z zadania 1.

Ważne: elita **nie jest wyłączona z selekcji**. Najlepszy osobnik nadal może zostać rodzicem (i
zwykle zostaje), więc jego geny trafiają także do potomków.

### Co daje elitaryzm

- **Monotoniczność:** najlepsze przystosowanie w populacji nigdy się nie pogarsza. W zadaniu 1
  najlepszy osobnik mógł zginąć przez mutację i trzeba go było zapamiętywać osobno.
- **Bezpieczniejsza eksploracja:** skoro najlepsze rozwiązanie jest chronione, można mocniej
  mutować resztę populacji bez ryzyka utraty postępu. W badaniach optymalne `p_m` dla resetu
  wzrosło z 0,05 (bez elity) do 0,1 (z elitą).

### Ryzyko

Za duża elita zmniejsza **różnorodność**: kopie tych samych najlepszych osobników dominują
populację, a selekcja wybiera je jako rodziców coraz częściej. W badaniach `e = 5` (25% populacji)
dawało gorsze wyniki niż `e = 1` lub `e = 2`, szczególnie w połączeniu z silną selekcją (turniej
`k = 5`).

### Związek z innymi schematami sukcesji

- **Sukcesja pokoleniowa** (zadanie 1): `e = 0`, wszyscy rodzice giną.
- **Sukcesja elitarna** (zadanie 2): przeżywa `e` najlepszych rodziców.
- **Sukcesja (μ + λ)**: rodzice i potomkowie konkurują razem, przeżywa najlepsza część z obu grup.
  To skrajnie elitarny wariant.
- **Sukcesja z częściowym zastępowaniem** (*steady state*): w każdym kroku wymienia się tylko
  jednego lub kilku osobników.

---

## 3. Metody selekcji

### Presja selekcyjna

**Presja selekcyjna** określa, jak bardzo selekcja faworyzuje najlepszych. Wygodna miara to
**oczekiwana liczba kopii najlepszego osobnika** w puli rodziców (przy losowaniu N rodziców):

- 1 kopia oznacza brak presji (wybór losowy),
- więcej kopii oznacza silniejszą presję.

Kompromis:

- **za duża presja:** populacja szybko wypełnia się kopiami jednego osobnika (przedwczesna
  zbieżność),
- **za mała presja:** dobre osobniki nie rozprzestrzeniają się i algorytm przypomina
  przeszukiwanie losowe.

### Selekcja turniejowa (przypomnienie)

Losujemy `k` osobników, rodzicem zostaje najlepszy z nich. Presję reguluje `k`: przy N osobnikach
najlepszy wygrywa turniej z prawdopodobieństwem `1 − (1 − 1/N)^k`. Liczy się tylko **kolejność**
osobników, a nie wartości `F`.

### Selekcja ruletkowa (proporcjonalna)

**Selekcja ruletkowa** wybiera osobnika *i* z prawdopodobieństwem proporcjonalnym do jego
przystosowania:

```
P(i) = F_i / Σ_j F_j
```

Nazwa pochodzi od koła ruletki, na którym każdy osobnik ma wycinek o szerokości `P(i)`. Losowanie
N rodziców to N obrotów koła (ze zwracaniem).

```
         ┌───────────────────────────────────────────────┐
koło:    │ osobnik 1 (32,5%) │ osobnik 3 (26,4%) │ 0 │ 2 │
         └───────────────────────────────────────────────┘
                    ↑ wskazówka losuje punkt
```

Kod: `roulette_selection` w [ga.py](ga.py).

**Wady ruletki:** wynik zależy od **skali** funkcji `F`, a nie tylko od kolejności osobników.

- **Na początku**, gdy jeden osobnik jest dużo lepszy od reszty, może zdominować losowanie
  (superosobnik), co grozi przedwczesną zbieżnością.
- **Pod koniec**, gdy wszystkie osobniki mają podobne `F`, presja niemal znika. Przykład z naszego
  problemu: jadłospisy za 8,50 zł i 10,00 zł mają `F = 1/9,5 = 0,105` i `F = 1/11 = 0,091`. Lepszy
  jest wybierany tylko o ok. 15% częściej, chociaż jest o 1,50 zł tańszy.

Klasyczne środki zaradcze to **skalowanie przystosowania** (liniowe, sigma) albo zastąpienie
ruletki selekcją rankingową. W zadaniu ich nie stosujemy. Słaba presja ruletki okazała się zaletą
w połączeniu z elitaryzmem (patrz punkt 9).

### Selekcja rankingowa (liniowa)

**Selekcja rankingowa** najpierw sortuje osobniki według przystosowania i nadaje im **rangi**: od 0
(najgorszy) do N − 1 (najlepszy). Prawdopodobieństwo wyboru zależy tylko od rangi, a nie od
wartości `F`. W wariancie liniowym:

```
P(r) = (2 − s) / N  +  2 · r · (s − 1) / (N · (N − 1))
```

Parametr `s ∈ [1, 2]` to **presja selekcyjna**. Oznacza oczekiwaną liczbę kopii najlepszego
osobnika, a najgorszy dostaje `2 − s` kopii:

- `s = 1`: wszystkie osobniki mają równe szanse (brak presji),
- `s = 2`: najgorszy nigdy nie jest wybierany, najlepszy dostaje średnio 2 kopie.

Kod: `ranking_selection` w [ga.py](ga.py).

Zalety:

- presja jest **stała** przez cały przebieg i niezależna od skali `F` (nie ma problemu ruletki),
- presję łatwo regulować jednym parametrem.

Wada: wymaga sortowania populacji, ale przy N = 20 ten koszt jest pomijalny.

### Porównanie na przykładzie

Populacja z zadania 1 (N = 4). W tabeli podano prawdopodobieństwo wyboru w jednym losowaniu
i oczekiwaną liczbę kopii przy 4 losowaniach (w nawiasie):

| osobnik | f [zł] | F | ranga | ruletka | ranking s = 1,5 | ranking s = 2,0 | turniej k = 3 |
|---|---|---|---|---|---|---|---|
| 1 (najlepszy) | 299,59 | 0,00333 | 3 | 32,5% (1,30) | 37,5% (1,50) | 50,0% (2,00) | 57,8% (2,31) |
| 3 | 370,29 | 0,00269 | 2 | 26,4% (1,05) | 29,2% (1,17) | 33,3% (1,33) | 29,7% (1,19) |
| 0 | 451,58 | 0,00221 | 1 | 21,6% (0,86) | 20,8% (0,83) | 16,7% (0,67) | 10,9% (0,44) |
| 2 (najgorszy) | 500,80 | 0,00199 | 0 | 19,5% (0,78) | 12,5% (0,50) | 0,0% (0,00) | 1,6% (0,06) |

Prawdopodobieństwa turnieju z `k = 3` wynikają z tego, że osobnik o randze `r` wygrywa, gdy jest
najlepszy wśród 3 wylosowanych: `P(r) = ((r + 1)³ − r³) / 4³`.

Wnioski z tabeli:

- **Ruletka ma najsłabszą presję.** Najlepszy osobnik ma tylko 1,30 kopii, choć jest o 200 zł
  tańszy od najgorszego. Powodem jest to, że wszystkie `F` są tu bardzo małe i podobne.
- **Ranking z `s = 2,0`** całkowicie eliminuje najgorszego.
- **Turniej z `k = 3`** ma najsilniejszą presję z tych metod.

---

## 4. Metody krzyżowania

### Maska krzyżowania

Wszystkie trzy metody da się opisać jednym schematem. Losujemy **maskę**: wektor 21 wartości
prawda/fałsz. Na pozycjach, gdzie maska ma wartość „prawda”, rodzice wymieniają się genami:

```
dziecko 1 = A tam, gdzie maska = 0;  B tam, gdzie maska = 1
dziecko 2 = B tam, gdzie maska = 0;  A tam, gdzie maska = 1
```

Metody różnią się tylko tym, jak powstaje maska (funkcje `*_mask` w [ga.py](ga.py)):

| metoda | maska | średnio wymienianych genów (z 21) |
|---|---|---|
| jednopunktowe | `000000001111111111111`: jedynki od losowego punktu do końca | 10,5 |
| dwupunktowe | `000001111111000000000`: jedynki w środkowym odcinku `[a, b)` | 7,0 |
| równomierne | `110011110110100010011`: każdy bit losowany z prawdopodobieństwem 1/2 | 10,5 |

### Krzyżowanie dwupunktowe

Losujemy dwa różne punkty cięcia `a < b` z `{1, …, 20}`. Rodzice wymieniają się środkowym
fragmentem `[a, b)`, a początek i koniec zostają na miejscu.

Zaleta względem jednopunktowego: **koniec chromosomu nie jest zawsze wymieniany razem ze
środkiem**. W jednopunktowym gen 20 (oliwa) zmienia rodzica przy każdym krzyżowaniu, a gen 0
(płatki) nigdy. W dwupunktowym pierwszy i ostatni gen traktowane są podobnie, bo chromosom można
sobie wyobrazić jako pierścień, z którego wycinamy odcinek.

### Krzyżowanie równomierne (jednorodne)

Każdy gen dziecka pochodzi od rodzica A lub B **niezależnie**, z prawdopodobieństwem 1/2.

- Zaleta: nie zależy od **kolejności genów** w chromosomie. Geny 0 i 20 tak samo łatwo trafiają do
  dziecka razem, jak geny 0 i 1.
- Wada: silnie **rozbija bloki** dobrych genów leżących obok siebie (patrz niżej).

### Obciążenie pozycyjne i rozbijanie schematów

**Obciążenie pozycyjne** (*positional bias*) oznacza, że prawdopodobieństwo przekazania dwóch genów
razem zależy od ich odległości w chromosomie.

- W jednopunktowym geny sąsiednie prawie zawsze przechodzą razem, a geny 0 i 20 nigdy.
- W równomiernym obciążenia pozycyjnego nie ma.

Związek z **twierdzeniem o schematach** (zadanie 1): krótkie schematy (dobre geny blisko siebie)
przetrwają krzyżowanie jedno- i dwupunktowe z dużym prawdopodobieństwem, a w równomiernym są często
rozbijane. Jeśli kolejność genów w chromosomie nie odpowiada zależnościom w problemie, ta ochrona
nic nie daje i równomierne bywa lepsze.

W naszym problemie wpływ krzyżowania okazał się mały: średnie trzech metod różniły się o ok. 0,1 zł,
czyli w granicach szumu.

---

## 5. Operatory mutacji

### Sąsiedztwo operatora

Każdy operator mutacji wyznacza **sąsiedztwo** rozwiązania, czyli zbiór rozwiązań osiągalnych
jedną mutacją. Od niego zależy, jakie kroki może wykonać algorytm.

| operator | sąsiedztwo jadłospisu |
|---|---|
| reset (1 gen) | zmiana liczby porcji jednego produktu na dowolną dozwoloną |
| ±1 (1 gen) | dodanie lub odjęcie jednej porcji jednego produktu |
| inwersja | przestawienie liczb porcji w odcinku produktów (przeniesienie porcji między produktami) |

**Optimum lokalne jest zawsze względne:** rozwiązanie może być lokalnie optymalne dla jednego
operatora, a dla innego nie. Dlatego dobór operatora mutacji ma tak duży wpływ na wyniki.

### Mutacja ±1 (creep)

Każdy gen z prawdopodobieństwem `p_m` zmienia się o **jedną porcję**, w górę lub w dół (kierunek
losowany z prawdopodobieństwem 1/2). Jeśli krok wyszedłby poza zakres `{0, …, max_i}`, wykonujemy
go w przeciwną stronę: z 0 zawsze idziemy na 1, z `max_i` zawsze na `max_i − 1`.

Kod: `creep_mutation` w [ga.py](ga.py).

Cechy:

- **małe, lokalne kroki:** sąsiedni jadłospis różni się o jedną porcję,
- **zawsze coś zmienia:** w resecie nowa wartość może wypaść równa starej, a tu nie,
- dobra do **dopracowywania** rozwiązania, ale słabo wychodzi z optimum lokalnego, bo daleki skok
  wymaga wielu kroków po kolei.

Przykład: w dziecku 1 z zadania 1 (f = 210,18 zł) usunięcie jednego jabłka (gen 15: 3 → 2) daje
f = 173,29 zł.

### Mutacja przez inwersję

**Inwersja** to operator zaproponowany przez Hollanda, klasycznie używany przy reprezentacji
permutacyjnej (np. w problemie komiwojażera odwraca kolejność odwiedzanych miast). Działanie:

1. z prawdopodobieństwem `p_m` (**na chromosom**, a nie na gen) wybieramy osobnika do mutacji,
2. losujemy dwie różne pozycje `a < b` (każda z 210 par jest równie prawdopodobna),
3. odwracamy kolejność genów w odcinku `[a, b]`.

Przykład dla odcinka `[4, 7]` (pokazane pierwsze 10 genów):

```
pozycja:  0  1  2  3   4  5  6  7   8  9
przed:   [2, 1, 0, 2, |1, 0, 1, 2|, 0, 1]
po:      [2, 1, 0, 2, |2, 1, 0, 1|, 0, 1]
                       └ odwrócone ┘
```

Kod: `inversion_mutation` w [ga.py](ga.py).

**Co inwersja oznacza w problemie diety.** W naszej reprezentacji pozycja genu to konkretny
produkt, więc inwersja **przenosi porcje między produktami**. Liczby porcji „przesiadają się” na
inne produkty, a ich suma (przed naprawą, opisaną niżej) się nie zmienia. To ruch typu „zamiast
produktu A zjedz produkt B”.

Przykład zamiany dwóch sąsiednich produktów, odcinek `[17, 18]`:

```
                 ... orzechy włoskie  masło orzechowe ...
przed:   [ ...        1                 0           ... ]   f = 9,50 zł
po:      [ ...        0                 1           ... ]   f = 8,60 zł
```

Orzechy włoskie (195 kcal, 19,5 g tłuszczu, 1,80 zł) zostały zastąpione masłem orzechowym
(180 kcal, 15 g tłuszczu, 0,90 zł). Wartości odżywcze prawie się nie zmieniły, a jadłospis
potaniał o 0,90 zł. Podobnie odcinek `[1, 2]` zamienia chleb (1,20 zł) na ryż (0,80 zł) i obniża
koszt z 9,30 do 8,90 zł.

### Naprawa (repair)

Produkty mają różne limity porcji, np. łosoś najwyżej 1 porcję, a jabłko 3. Po inwersji wartość 3
może trafić na pozycję produktu z limitem 2. Taki chromosom łamałby ograniczenie kostkowe, więc
jest **naprawiany**: wartość przycinamy do limitu, `x_i ← min(x_i, max_i)`.

**Naprawa** to druga, obok funkcji kary, klasyczna metoda radzenia sobie z ograniczeniami w AG.
Zamiast karać niedopuszczalnego osobnika, zamieniamy go na najbliższego dopuszczalnego. W zadaniu
stosujemy obie metody:

- **naprawę** dla limitów porcji (łatwych, kostkowych),
- **karę** dla wartości odżywczych (trudnych, sprzężonych ze sobą).

Przykład inwersji z naprawą. Dziecko 1 z zadania 1, odcinek `[13, 20]` (marchew … oliwa):

```
produkt:       marchew pomidor jabłko banan orzechy masło ser oliwa
limit:            2       2      3      2      2      2    3    3
przed:            2       0      3      2      0      1    0    3     suma 11, f = 210,18
odwrócone:        3       0      1      0      2      3    0    2
po naprawie:      2       0      1      0      2      2    0    2     suma 9,  f = 235,80
                  ↑                            ↑
           przycięte 3 → 2              przycięte 3 → 2
```

Ten przykład pokazuje też, że inwersja (jak każda mutacja) może pogorszyć osobnika: tu f wzrosło
z 210,18 do 235,80 zł.

### Dlaczego inwersja wymaga dużego `p_m`

Reset i ±1 działają **na gen**: przy `p_m = 0,1` zmienia się średnio 2,1 genu w osobniku. Inwersja
działa **na chromosom**: przy `p_m = 0,8` 80% potomków dostaje jedną inwersję. Te wartości nie są
porównywalne wprost, dlatego każdy operator ma w badaniach własną siatkę `p_m`.

---

## 6. Pojęcia używane w badaniach

### Plan czynnikowy, czynnik, poziom

- **Czynnik** to badana cecha algorytmu, np. metoda selekcji.
- **Poziom** to konkretna wartość czynnika, np. „ruletka”.
- **Konfiguracja** to jedna kombinacja poziomów wszystkich czynników.
- **Pełny plan czynnikowy** (*full factorial design*) sprawdza **wszystkie** kombinacje poziomów.

W etapie 1 mamy 6 (selekcja) × 4 (elita) × 3 (krzyżowanie) × 3 (`p_c`) × 12 (mutacja i `p_m`) =
**2592 konfiguracje**.

Alternatywa to badanie „jeden czynnik naraz” (zmieniamy jeden, resztę ustalamy). Jest tańsze, ale
nie wykrywa **interakcji**.

### Efekt główny i interakcja

- **Efekt główny** czynnika to średnia zmiana wyniku przy zmianie jego poziomu, uśredniona po
  wszystkich pozostałych czynnikach. Przykład: średnia danej metody dla `e = 0` to 11,21 zł, a dla
  `e = 2` to 9,60 zł.
- **Interakcja** występuje, gdy wpływ jednego czynnika **zależy od poziomu innego**. Przykład:
  najlepsze `p_m` dla resetu wynosi 0,05 bez elity i 0,1 z elitą. Elitaryzm i mutacja oddziałują
  na siebie. Drugi przykład: bez elity ruletka jest dużo gorsza od turnieju, a z elitą prawie mu
  dorównuje.

### „Średnia danej metody” i „najlepsza konfiguracja”

Dla każdego poziomu czynnika raportujemy dwie liczby, bo odpowiadają na różne pytania:

| miara | pytanie | przykład |
|---|---|---|
| średnia danej metody | jak metoda radzi sobie przeciętnie, także przy złych parametrach (odporność) | ruletka: 9,85 zł, najlepsza ze wszystkich selekcji |
| najlepsza konfiguracja | ile metoda może dać po dobrym dostrojeniu (potencjał) | turniej: 8,55 zł, najlepsza ze wszystkich selekcji |

Metoda odporna nie musi być najlepsza po dostrojeniu i odwrotnie.

### Błąd standardowy średniej

Średnia z `n` uruchomień też jest losowa. Jej rozrzut mierzy **błąd standardowy**:

```
SE = s / √n
```

gdzie `s` to odchylenie standardowe pojedynczych wyników. W etapie 1 `s ≈ 0,65 zł` i `n = 30`, więc
`SE ≈ 0,12 zł`. Różnice średnich mniejsze niż ok. 2 · SE ≈ 0,25 zł nie są rozstrzygające.

### Przekleństwo zwycięzcy i walidacja

Gdy wybieramy najlepszą z 2592 średnich, wybieramy konfigurację, która była **dobra albo miała
szczęście** w tych 30 losowaniach. Jej wynik jest więc zawyżony. Zjawisko to nazywa się
**przekleństwem zwycięzcy** (*winner's curse*) albo **nadmiernym dopasowaniem do ziaren**. To ten
sam problem co przeuczenie modelu na zbiorze treningowym.

Rozwiązaniem jest **walidacja**: kandydatów uruchamiamy ponownie na **nowych ziarnach** (1000–1099),
których nie użyto przy wyborze. To odpowiednik zbioru testowego w uczeniu maszynowym. W badaniach
konfiguracje z czołówki pogorszyły się w walidacji o 0,2–0,4 zł, a zwycięska nie (8,55 → 8,54 zł).

### Test Manna–Whitneya i p-wartość

**Test statystyczny** sprawdza, czy różnica między dwiema grupami wyników może wynikać z
przypadku.

- **Hipoteza zerowa H₀:** obie konfiguracje dają wyniki z tego samego rozkładu (żadna nie jest
  lepsza).
- **p-wartość:** prawdopodobieństwo uzyskania tak dużej (lub większej) różnicy, **gdyby H₀ była
  prawdziwa**. Mała p-wartość (zwykle < 0,05) oznacza, że różnica raczej nie jest przypadkowa.

**Test Manna–Whitneya** (test sumy rang Wilcoxona) porównuje dwie grupy na podstawie **rang**:
łączy oba zbiory wyników, sortuje je i sprawdza, czy wyniki jednej grupy systematycznie zajmują
niższe miejsca. Jest **nieparametryczny**, czyli nie zakłada rozkładu normalnego. To ważne, bo
nasze wyniki go nie mają: są ograniczone od dołu przez optimum 7,70 zł i skupione na kilku
wartościach (np. 46% uruchomień zwycięzcy kończy się na 8,10 zł).

Stosujemy wariant **jednostronny**: H₁ mówi „zwycięzca daje mniejsze f”.

### Mediana i wykres pudełkowy

- **Mediana** to wartość środkowa: połowa uruchomień jest lepsza, połowa gorsza. W przeciwieństwie
  do średniej jest odporna na pojedyncze bardzo złe uruchomienia.
- **Wykres pudełkowy** (*boxplot*) pokazuje rozkład wyników:
  - pudełko obejmuje środkowe 50% uruchomień (od 1. do 3. kwartyla),
  - kreska w pudełku to mediana,
  - wąsy sięgają do najdalszych typowych wyników,
  - kropki poza wąsami to wartości odstające.

### Budżet obliczeniowy

**Budżet** to liczba ocen funkcji przystosowania, czyli główny koszt AG. Uczciwe porównanie
algorytmów wymaga **równego budżetu**. Wszystkie konfiguracje mają N = 20 i 300 pokoleń, czyli
ok. 6000 ocen. W etapie 3 sprawdzamy, czy przy tym samym budżecie lepiej mieć większą populację
i mniej pokoleń (np. N = 100 i 60 pokoleń), czy odwrotnie.

---

## 7. Algorytm krok po kroku na przykładzie

### Pseudokod

```
wczytaj dane, ustaw konfigurację (N, G, selekcja, e, krzyżowanie, p_c, mutacja, p_m, seed)
P ← N losowych chromosomów                              # krok 1: inicjalizacja
oceń F dla każdego osobnika w P                         # krok 2: ocena

dla g = 0, 1, …, G:
    zaktualizuj najlepszego, zapisz statystyki          # (jak w zadaniu 1)
    jeśli g = G: zakończ
    E ← e najlepszych osobników z P                     # krok 3: elita
    R ← selekcja(P, N − e)                              # krok 4: N − e rodziców
    D ← krzyżowanie(R, p_c)                             # krok 5: N − e potomków
    D ← mutacja(D, p_m)                                 # krok 6
    P ← E ∪ D; oceń F dla każdego osobnika w P          # krok 7: nowa populacja

zwróć najlepszego
```

Odpowiada to funkcji `run_ga` w [ga.py](ga.py). W porównaniu z zadaniem 1 doszły krok 3 i
wymienne operatory w krokach 4–6.

Przykład korzysta z populacji z zadania 1 (N = 4, ziarno 42) i elity `e = 1`.

### Krok 1–2: inicjalizacja i ocena

Bez zmian względem zadania 1:

| osobnik | chromosom | f [zł] | F |
|---|---|---|---|
| 0 | `[0, 3, 1, 1, 1, 2, 0, 2, 0, 0, 1, 1, 2, 2, 2, 3, 1, 0, 2, 1, 2]` | 451,58 | 0,00221 |
| 1 | `[1, 0, 2, 2, 2, 1, 2, 1, 1, 1, 0, 0, 1, 2, 0, 3, 2, 0, 1, 0, 3]` | 299,59 | **0,00333** |
| 2 | `[2, 1, 0, 2, 1, 2, 2, 2, 2, 0, 0, 0, 1, 0, 1, 0, 2, 2, 2, 2, 1]` | 500,80 | 0,00199 |
| 3 | `[2, 1, 0, 2, 1, 0, 1, 2, 0, 1, 0, 1, 1, 0, 0, 2, 2, 2, 1, 0, 3]` | 370,29 | 0,00269 |

### Krok 3: elita

Sortujemy osobniki według `F`: 1, 3, 0, 2. Przy `e = 1` elitą jest **osobnik 1** i trafia do
następnego pokolenia bez zmian, bez względu na to, co stanie się w krokach 4–6.

Zostają `N − e = 3` miejsca dla potomków.

### Krok 4: selekcja N − e = 3 rodziców

Rodziców losujemy z **całej** populacji, łącznie z elitą. Prawdopodobieństwa wyboru dla trzech
metod (z tabeli w punkcie 3):

| osobnik | ruletka | ranking s = 2,0 | turniej k = 3 |
|---|---|---|---|
| 1 | 32,5% | 50,0% | 57,8% |
| 3 | 26,4% | 33,3% | 29,7% |
| 0 | 21,6% | 16,7% | 10,9% |
| 2 | 19,5% | 0,0% | 1,6% |

Załóżmy, że wylosowano rodziców `[3, 1, 0]`. Pierwsza para (3, 1) będzie krzyżowana, a trzeci
rodzic (0) nie ma pary, więc przechodzi do kroku 6 bez krzyżowania.

### Krok 5: krzyżowanie pary (A = osobnik 3, B = osobnik 1)

Porównanie trzech metod na tej samej parze rodziców (A: f = 370,29 zł, B: f = 299,59 zł):

**Jednopunktowe** (cięcie po genie 10, przykład z zadania 1):

```
maska:      [0 0 0 0 0 0 0 0 0 0 0 1 1 1 1 1 1 1 1 1 1]
dziecko 1:  [2, 1, 0, 2, 1, 0, 1, 2, 0, 1, 0, 0, 1, 2, 0, 3, 2, 0, 1, 0, 3]   f = 210,18
dziecko 2:  [1, 0, 2, 2, 2, 1, 2, 1, 1, 1, 0, 1, 1, 0, 0, 2, 2, 2, 1, 0, 3]   f = 482,58
```

**Dwupunktowe** (odcinek `[5, 12)`: kurczak, jajka, twaróg, mleko, jogurt, łosoś, soczewica):

```
maska:      [0 0 0 0 0 1 1 1 1 1 1 1 0 0 0 0 0 0 0 0 0]
dziecko 1:  [2, 1, 0, 2, 1, 1, 2, 1, 1, 1, 0, 0, 1, 0, 0, 2, 2, 2, 1, 0, 3]   f = 347,12
dziecko 2:  [1, 0, 2, 2, 2, 0, 1, 2, 0, 1, 0, 1, 1, 2, 0, 3, 2, 0, 1, 0, 3]   f = 332,59
```

Wymieniono tylko „blok białkowy” w środku chromosomu. Oba dzieci są pomiędzy rodzicami.

**Równomierne** (losowa maska):

```
maska:      [1 1 0 0 1 1 1 1 0 1 1 0 1 0 0 0 1 0 0 1 1]
dziecko 1:  [1, 0, 0, 2, 2, 1, 2, 1, 0, 1, 0, 1, 1, 0, 0, 2, 2, 2, 1, 0, 3]   f = 279,27
dziecko 2:  [2, 1, 2, 2, 1, 0, 1, 2, 1, 1, 0, 0, 1, 2, 0, 3, 2, 0, 1, 0, 3]   f = 390,61
```

Dziecko 1 jest lepsze od obu rodziców (279,27 < 299,59 zł).

Podsumowanie:

| metoda | dziecko 1 | dziecko 2 | lepsze od obu rodziców? |
|---|---|---|---|
| jednopunktowe | 210,18 | 482,58 | tak (dziecko 1) |
| dwupunktowe | 347,12 | 332,59 | nie |
| równomierne | 279,27 | 390,61 | tak (dziecko 1) |

Wynik pojedynczego krzyżowania jest loterią. O jakości metody decyduje dopiero statystyka z wielu
pokoleń i uruchomień.

### Krok 6: mutacja potomków

Każdy z 3 potomków (2 dzieci i niekrzyżowany rodzic 0) przechodzi mutację wybranym operatorem:

- **reset** (`p_m` na gen): przykład z zadania 1, gen 17 w dziecku 2: 2 → 0, f: 482,58 → 340,98 zł,
- **±1** (`p_m` na gen): np. gen 15 (jabłko) w dziecku 1: 3 → 2, f: 210,18 → 173,29 zł,
- **inwersja** (`p_m` na chromosom): np. odcinek `[13, 20]` w dziecku 1 z naprawą (punkt 5),
  f: 210,18 → 235,80 zł.

Elita (osobnik 1) **nie jest mutowana**.

### Krok 7: nowa populacja

```
nowa populacja = [ osobnik 1 (elita, f = 299,59) | potomek 1 | potomek 2 | potomek 3 ]
```

Liczymy `F` dla nowej populacji i wracamy do początku pętli. Dzięki elicie najlepszy osobnik nowej
populacji ma f ≤ 299,59 zł, bez względu na to, jak udały się potomki.

---

## 8. Przebieg całego uruchomienia

To samo ziarno (1007), N = 20, 300 pokoleń, dwie konfiguracje:

- **zadanie 1:** turniej k = 3, bez elity, jednopunktowe `p_c = 0,8`, reset `p_m = 0,05`,
- **zwycięzca zadania 2:** turniej k = 3, elita 1, jednopunktowe `p_c = 1,0`, inwersja `p_m = 0,8`.

Wartości `f` w złotówkach, „unikalne” to odsetek różnych chromosomów w populacji:

| pokolenie | zad. 1: najlepszy w pop. | zad. 1: średnia | zad. 1: najlepszy dotąd | zad. 1: unikalne | zad. 2: najlepszy w pop. | zad. 2: średnia | zad. 2: unikalne |
|---|---|---|---|---|---|---|---|
| 0 | 102,50 | 283,65 | 102,50 | 1,00 | 102,50 | 283,65 | 1,00 |
| 1 | 17,80 | 103,74 | 17,80 | 1,00 | 19,50 | 85,51 | 1,00 |
| 5 | 15,70 | 27,02 | 15,70 | 0,80 | 19,50 | 51,82 | 0,95 |
| 10 | 16,00 | 21,86 | 15,70 | 0,75 | 11,20 | 22,39 | 0,95 |
| 25 | 10,80 | 19,43 | **9,60** | 0,90 | 11,00 | 29,12 | 1,00 |
| 50 | 10,60 | 16,56 | 9,60 | 0,70 | 10,40 | 28,45 | 1,00 |
| 100 | 10,50 | 15,61 | 9,60 | 0,80 | **7,70** | 23,49 | 0,95 |
| 200 | 10,10 | 16,64 | 9,60 | 0,85 | 7,70 | 30,07 | 0,75 |
| 300 | 10,10 | 12,30 | 9,60 | 0,45 | 7,70 | 20,79 | 0,60 |

W konfiguracji z elitą „najlepszy w populacji” jest zawsze równy „najlepszemu dotąd”, więc ta
kolumna nie jest powtórzona.

Co widać:

1. **Zadanie 1 utknęło w 18. pokoleniu.** Najlepszy wynik (9,60 zł) pojawił się w pokoleniu 18 i
   później się nie poprawił. Najlepszy osobnik w populacji **pogorszył się 14 razy**, bo był
   niszczony przez mutację lub nie wygrywał turnieju. Pod koniec populacja jest mało zróżnicowana
   (45% unikalnych).
2. **Zwycięzca zadania 2 znalazł optimum 7,70 zł w pokoleniu 68.** Najlepszy osobnik ani razu się
   nie pogorszył (elita).
3. **Średnia populacji jest w zadaniu 2 wyższa** (20–30 zł wobec 12–19 zł od 25. pokolenia). To skutek mocnej
   mutacji (80% potomków dostaje inwersję): populacja jest bardziej „rozrzucona” i bada więcej
   jadłospisów. Bez elity taka mutacja byłaby szkodliwa, bo niszczyłaby najlepszego osobnika. Z
   elitą jest bezpieczna.
4. **Różnorodność jest wyższa w zadaniu 2:** 95–100% unikalnych osobników przez pierwsze 100
   pokoleń.

---

## 9. Dlaczego zwycięska kombinacja działa

Zwycięska konfiguracja: **turniej k = 3, elita 1, krzyżowanie jednopunktowe `p_c = 1,0`, inwersja
`p_m = 0,8`**. Średnio 8,54 zł wobec 10,09 zł w zadaniu 1.

### Elitaryzm umożliwia mocną eksplorację

Elita gwarantuje, że postęp nie zostanie utracony. Algorytm może więc mutować bardzo agresywnie
(80% potomków) i utrzymywać dużą różnorodność, a mimo to najlepsze rozwiązanie stale się poprawia.
To równowaga **eksploracji** (mutacja, różnorodność) i **eksploatacji** (selekcja, elita).

### Inwersja wykonuje ruchy, których potrzebuje ten problem

Blisko optimum jadłospis spełnia już wszystkie ograniczenia, a poprawa polega na **zamianie
droższego produktu na tańszy o podobnych wartościach odżywczych**. Taki ruch wymaga zmiany dwóch
genów naraz (jeden w dół, drugi w górę).

Porównanie prawdopodobieństwa wykonania jednej konkretnej zamiany (orzechy → masło orzechowe,
przykład z punktu 5) w jednym potomku, pomijając krzyżowanie:

| operator | jak musi zadziałać | prawdopodobieństwo |
|---|---|---|
| reset, `p_m = 0,1` | gen 17 → 0 i gen 18 → 1, reszta bez zmian | ok. 0,03% |
| ±1, `p_m = 0,1` | gen 17 w dół i gen 18 w górę, reszta bez zmian | ok. 0,07% |
| inwersja, `p_m = 0,8` | wylosowanie odcinka `[17, 18]` (1 z 210) | ok. 0,38% |

Inwersja wykonuje taki ruch ok. **13 razy częściej** niż reset. Potwierdza to też pomiar na 555
dobrych, ale nieoptymalnych rozwiązaniach z walidacji: jedna inwersja poprawiała wynik w 0,84%
prób, mutacja ±1 w 0,58%, a reset w 0,44%. W 91% przypadków inwersja nie zmieniała łącznej liczby
porcji.

### Turniej z k = 3 daje umiarkowaną, stałą presję

Turniej zależy tylko od kolejności osobników, więc jego presja nie zanika pod koniec przebiegu, jak
w ruletce. Z elitą wszystkie metody selekcji dają podobne wyniki (8,54–8,88 zł w walidacji), ale
turniej był najlepszy.

### Dlaczego nadal nie zawsze znajduje optimum

Zwycięska konfiguracja trafia w 7,70 zł w 6% uruchomień, a **w 46% kończy na 8,10 zł**. Ten
jadłospis:

```
2 × płatki owsiane, 1 × ryż, 2 × makaron, 1 × twaróg, 2 × masło orzechowe, 1 × oliwa
```

to **silne optimum lokalne**. Sprawdzono, że nie poprawia go:

- żadna zmiana jednego genu,
- żadna zmiana dwóch genów naraz,
- żadna inwersja.

Do optimum (7,70 zł) trzeba zmienić cztery geny jednocześnie: −1 ryż, −1 twaróg, +1 soczewica,
+1 oliwa. Żaden z operatorów nie robi tego jednym krokiem, a kroki pośrednie są gorsze, więc
selekcja je odrzuca. Możliwe ulepszenia (wykraczające poza zadanie):

- **lokalne przeszukiwanie** najlepszego osobnika, np. sprawdzenie wszystkich zmian 3–4 genów
  (algorytm memetyczny),
- **restart** populacji po wykryciu stagnacji,
- **połączenie operatorów**, np. inwersja i reset jednocześnie, żeby mieć i zamiany, i duże skoki.
