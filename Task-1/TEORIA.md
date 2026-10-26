# Zadanie 1: teoria i działanie algorytmu krok po kroku

Ten dokument wyjaśnia pojęcia teoretyczne użyte w zadaniu i pokazuje, co dokładnie dzieje się
w algorytmie genetycznym (AG) z [ga.py](ga.py). Wszystkie liczby w przykładach zostały policzone
na prawdziwych danych z [diet_data.py](diet_data.py) przy użyciu funkcji z [ga.py](ga.py).

Spis treści:

1. [Problem optymalizacyjny](#1-problem-optymalizacyjny)
2. [Słownik pojęć algorytmu genetycznego](#2-słownik-pojęć-algorytmu-genetycznego)
3. [Pojęcia używane w eksperymentach](#3-pojęcia-używane-w-eksperymentach)
4. [Algorytm krok po kroku na przykładzie](#4-algorytm-krok-po-kroku-na-przykładzie)
5. [Przebieg całego uruchomienia](#5-przebieg-całego-uruchomienia)
6. [Dlaczego to w ogóle działa](#6-dlaczego-to-w-ogóle-działa)

---

## 1. Problem optymalizacyjny

### Problem optymalizacji

**Problem optymalizacji** polega na znalezieniu takiego rozwiązania `x` ze zbioru możliwych
rozwiązań, dla którego pewna funkcja (funkcja celu) przyjmuje najmniejszą (minimalizacja) lub
największą (maksymalizacja) wartość.

W zadaniu: spośród wszystkich możliwych jadłospisów szukamy **najtańszego**, który dostarcza
odpowiednią ilość kcal, białka, tłuszczu, węglowodanów i błonnika. Jest to wariant klasycznego
**problemu diety** (Stigler, 1945), jednego z pierwszych zastosowań programowania liniowego.

### Zmienne decyzyjne

**Zmienne decyzyjne** to wielkości, które wybieramy. Tutaj `x_i` oznacza liczbę porcji produktu
*i* (i = 1…21). Są to liczby **całkowite** (nie zjemy 1,37 porcji), więc problem jest
**dyskretny** (kombinatoryczny).

### Ograniczenia

**Ograniczenia** to warunki, które rozwiązanie musi spełniać:

- **ograniczenia odżywcze**: dla każdego składnika `j` suma `Σ x_i · zawartość_ij` musi leżeć
  w przedziale `[min_j, max_j]`, np. energia w `[2300, 2500]` kcal,
- **ograniczenia kostkowe (zakresowe)**: `0 ≤ x_i ≤ max_i`, np. łosoś najwyżej 1 porcja dziennie.

### Rozwiązanie dopuszczalne i niedopuszczalne

- **Rozwiązanie dopuszczalne** spełnia wszystkie ograniczenia.
- **Rozwiązanie niedopuszczalne** łamie co najmniej jedno ograniczenie, np. ma 2600 kcal.

**Zbiór dopuszczalny** to zbiór wszystkich rozwiązań dopuszczalnych.

### Przestrzeń przeszukiwania

**Przestrzeń przeszukiwania** to zbiór wszystkich rozwiązań, które algorytm może rozważyć.
Tutaj każdy gen może przyjąć `max_i + 1` wartości, więc liczba wszystkich jadłospisów wynosi:

```
4^5 · 3^14 · 2^2 = 19 591 041 024  ≈  2 · 10^10
```

Sprawdzenie wszystkich (tzw. **przegląd zupełny**, *brute force*) byłoby bardzo kosztowne.
Dla porównania AG z N = 20 i 300 pokoleniami ocenia tylko `20 · 301 = 6020` osobników, czyli
mniej niż jedną trzymilionową część przestrzeni.

### Optimum globalne i lokalne

- **Optimum globalne** to najlepsze rozwiązanie w całym zbiorze dopuszczalnym. Tutaj kosztuje
  **7,70 zł**.
- **Optimum lokalne** to rozwiązanie, którego nie da się poprawić małą zmianą (np. dodaniem lub
  odjęciem jednej porcji), chociaż gdzie indziej istnieje lepsze. Algorytmy przeszukiwania
  lokalnego łatwo w nim utykają. AG próbuje tego unikać, bo pracuje na całej populacji i stosuje
  losowe operatory.

### Metaheurystyka

**Heurystyka** to metoda, która zwykle znajduje dobre rozwiązanie, ale **nie gwarantuje**
znalezienia optimum. **Metaheurystyka** to ogólny schemat heurystyki, który można zastosować do
wielu różnych problemów. Algorytm genetyczny jest metaheurystyką: nie musi nic wiedzieć
o strukturze problemu, wystarczy mu możliwość ocenienia każdego rozwiązania.

---

## 2. Słownik pojęć algorytmu genetycznego

### Algorytm genetyczny (AG)

**Algorytm genetyczny** to metoda optymalizacji inspirowana ewolucją biologiczną (Holland, 1975).
Utrzymuje zbiór rozwiązań (populację), który z pokolenia na pokolenie jest ulepszany przez:

1. **selekcję**: lepsze rozwiązania częściej zostają rodzicami („przetrwanie najlepiej
   przystosowanych”),
2. **krzyżowanie**: potomkowie powstają przez łączenie fragmentów rodziców,
3. **mutację**: potomkowie są losowo, lekko modyfikowani.

AG jest **algorytmem stochastycznym**: korzysta z losowości, więc dwa uruchomienia mogą dać różne
wyniki.

### Osobnik, populacja, pokolenie

| pojęcie | znaczenie ogólne | w zadaniu |
|---|---|---|
| **osobnik** | jedno rozwiązanie kandydujące | jeden jadłospis |
| **populacja** | zbiór osobników przetwarzany jednocześnie | N jadłospisów (domyślnie N = 20) |
| **rozmiar populacji N** | liczba osobników w populacji | parametr `--pop` |
| **pokolenie (generacja)** | jedna iteracja algorytmu: z populacji rodziców powstaje populacja potomków | 300 pokoleń |

### Chromosom, gen, allel, locus

| pojęcie | znaczenie ogólne | w zadaniu |
|---|---|---|
| **chromosom** | zakodowana postać osobnika | wektor 21 liczb całkowitych |
| **gen** | pojedyncza pozycja chromosomu | liczba porcji jednego produktu |
| **locus** | numer pozycji genu w chromosomie | numer produktu (0…20) |
| **allel** | konkretna wartość genu | np. 0, 1, 2 lub 3 porcje |

Przykład chromosomu (rozwiązanie optymalne):

```
locus:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20
allel: [2, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 2, 0, 2]
        ↑           ↑                    ↑                    ↑     ↑
     płatki      makaron             soczewica          masło orz.  oliwa
```

### Genotyp i fenotyp

- **Genotyp** to sam chromosom, czyli ciąg liczb, na którym działają operatory genetyczne.
- **Fenotyp** to rzeczywiste rozwiązanie, które z niego wynika, czyli konkretny jadłospis z jego
  kosztem i wartościami odżywczymi.

Tutaj przejście genotyp → fenotyp jest bardzo proste (gen = liczba porcji). W innych problemach
bywa skomplikowane, np. w kodowaniu binarnym liczba rzeczywista jest zapisana jako ciąg bitów.

### Reprezentacja (kodowanie)

**Reprezentacja** to sposób zapisania rozwiązania w postaci chromosomu. Najczęstsze rodzaje:

- **binarna**: chromosom to ciąg bitów 0/1 (klasyczny AG Hollanda),
- **całkowitoliczbowa**: chromosom to ciąg liczb całkowitych (**użyta w zadaniu**),
- **rzeczywista**: chromosom to ciąg liczb rzeczywistych,
- **permutacyjna**: chromosom to permutacja, np. kolejność miast w problemie komiwojażera.

Reprezentacja całkowitoliczbowa ma tu dwie zalety:

1. pasuje do natury problemu (jadłospis składa się z całych porcji),
2. limity porcji są spełnione **z definicji**. Losowanie, krzyżowanie i mutacja zawsze dają
   wartości z `{0, …, max_i}`, więc nie trzeba osobno pilnować ograniczeń kostkowych.

### Funkcja celu

**Funkcja celu** mierzy jakość rozwiązania z punktu widzenia problemu. W zadaniu ją
**minimalizujemy**:

```
f(x) = koszt(x) + W · V(x)
```

- `koszt(x) = Σ x_i · cena_i` to cena jadłospisu w złotówkach,
- `V(x)` to miara naruszenia ograniczeń (opisana niżej),
- `W = 200 zł` to waga kary.

Kod: `DietProblem.objective` w [ga.py](ga.py).

### Funkcja kary i metoda funkcji kary

AG sam z siebie nie rozumie ograniczeń: losowe operatory często tworzą jadłospisy
niedopuszczalne. **Metoda funkcji kary** nie odrzuca takich osobników, tylko **pogarsza ich ocenę**
proporcjonalnie do tego, jak bardzo łamią ograniczenia.

W zadaniu naruszenie liczone jest **względnie**, osobno dla każdego składnika:

```
V(x) = Σ_j [ max(0, min_j − s_j) / min_j  +  max(0, s_j − max_j) / max_j ]
```

gdzie `s_j` to ilość składnika `j` w jadłospisie. Dzielenie przez `min_j` lub `max_j` sprawia, że
różne jednostki (kcal i gramy) są porównywalne: 1% za mało białka waży tyle samo co 1% za dużo kcal.

Dla rozwiązania dopuszczalnego `V(x) = 0`, więc `f(x)` jest po prostu kosztem.

**Przykład.** Weźmy optimum i usuńmy z niego jedną porcję oliwy:

| | kcal | białko | tłuszcz | węgl. | błonnik |
|---|---|---|---|---|---|
| wartość | 2238 | 90,0 | 58,5 | 330 | 41 |
| zakres | 2300–2500 | 90–160 | 60–90 | 300–380 | 30–60 |
| naruszenie względne | 62/2300 = 0,0270 | 0 | 1,5/60 = 0,0250 | 0 | 0 |

```
V = 0,0270 + 0,0250 = 0,0520
f = 7,30 zł + 200 · 0,0520 = 7,30 + 10,39 = 17,69 zł
```

Jadłospis jest o 0,40 zł tańszy od optimum (7,70 zł), ale przez karę dostaje dużo gorszą ocenę.
Kara „opłaca się” tylko wtedy, gdy naruszenie jest bardzo małe, i to właśnie widać
w eksperymentach: niedopuszczalni zwycięzcy łamali ograniczenia najwyżej o ok. 1%.

**Dobór wagi kary** to kompromis:

- **za mała waga**: algorytm woli tanie, ale niedopuszczalne jadłospisy,
- **za duża waga**: każde naruszenie jest tak drogie, że różnice w koszcie przestają mieć
  znaczenie, a algorytm trudniej przechodzi przez obszary niedopuszczalne.

### Funkcja przystosowania (fitness)

**Funkcja przystosowania** mówi, jak dobrze osobnik jest „przystosowany do środowiska”. AG ją
zawsze **maksymalizuje**. Ponieważ nasz cel minimalizujemy, trzeba go odwrócić:

```
F(x) = 1 / (1 + f(x))
```

Własności:

- `F ∈ (0, 1]`, bo `f(x) ≥ 0`,
- mniejsze `f` daje większe `F`, czyli lepszego osobnika,
- „+1” w mianowniku zabezpiecza przed dzieleniem przez zero.

Przykłady:

| jadłospis | f(x) | F(x) |
|---|---|---|
| optimum | 7,70 | 1/8,70 = 0,11494 |
| optimum bez 1 porcji oliwy | 17,69 | 0,05350 |
| losowy jadłospis (osobnik 1 z przykładu niżej) | 299,59 | 0,00333 |

Kod: `DietProblem.fitness` w [ga.py](ga.py).

### Operatory genetyczne

**Operatory genetyczne** to procedury, które tworzą nową populację ze starej: selekcja,
krzyżowanie i mutacja. Krzyżowanie i mutację nazywa się też **operatorami wariacji**, bo tworzą
nowe rozwiązania, a selekcja tylko wybiera spośród istniejących.

### Selekcja

**Selekcja** wybiera osobniki, które zostaną rodzicami. Lepsi powinni być wybierani częściej, ale
słabsi nie mogą być całkowicie wykluczeni, bo to zabija różnorodność.

**Selekcja turniejowa** (użyta w zadaniu, `tournament_selection` w [ga.py](ga.py)):

1. losujemy `k` osobników z populacji (ze zwracaniem),
2. zwycięzcą turnieju jest ten z największym `F`,
3. zwycięzca trafia do puli rodziców,
4. powtarzamy N razy, żeby uzyskać N rodziców.

W zadaniu `k = 3`.

Zalety selekcji turniejowej:

- zależy tylko od **kolejności** osobników, a nie od wartości `F`, więc nie przeszkadza jej to, że
  `F` ma bardzo różne skale (0,002 vs 0,11),
- łatwo sterować presją selekcyjną przez zmianę `k`.

Dla porównania **selekcja ruletkowa** (proporcjonalna) wybiera osobnika z prawdopodobieństwem
`F_i / Σ F`. Jest wrażliwa na skalę: jeden bardzo dobry osobnik może zdominować całe losowanie.

### Presja selekcyjna

**Presja selekcyjna** określa, jak mocno selekcja faworyzuje najlepszych.

- **duża presja** (duże `k`): szybka zbieżność, ale ryzyko utraty różnorodności,
- **mała presja** (małe `k`, np. `k = 1` oznacza losowy wybór): wolne postępy, algorytm przypomina
  przeszukiwanie losowe.

### Krzyżowanie (rekombinacja)

**Krzyżowanie** tworzy potomków przez wymianę fragmentów chromosomów dwóch rodziców. Służy do
**łączenia dobrych cech** różnych rozwiązań.

**Prawdopodobieństwo krzyżowania `p_c`** określa, jaka część par jest krzyżowana. Pozostałe pary
przechodzą do potomstwa bez zmian (kopie rodziców).

**Krzyżowanie jednopunktowe** (użyte w zadaniu, `one_point_crossover` w [ga.py](ga.py)):

1. losujemy punkt cięcia `cut ∈ {1, …, 20}`, więc obie części są niepuste,
2. dziecko 1 = początek rodzica A + koniec rodzica B,
3. dziecko 2 = początek rodzica B + koniec rodzica A.

```
cut = 3
rodzic A: [a0 a1 a2 | a3 a4 ... a20]      dziecko 1: [a0 a1 a2 | b3 b4 ... b20]
rodzic B: [b0 b1 b2 | b3 b4 ... b20]  →   dziecko 2: [b0 b1 b2 | a3 a4 ... a20]
```

Inne warianty (niewykorzystane w zadaniu):

- **dwupunktowe**: wymiana środkowego fragmentu między dwoma punktami cięcia,
- **równomierne (jednorodne)**: każdy gen osobno losowo od A lub od B.

Krzyżowanie nie tworzy nowych wartości genów: dziecko ma tylko allele obecne u rodziców. Dlatego
samo krzyżowanie nie wystarcza i potrzebna jest mutacja.

### Mutacja

**Mutacja** wprowadza małe, losowe zmiany w pojedynczym osobniku. Jej zadania:

- dostarcza **nowego materiału genetycznego**, którego nie ma w populacji,
- utrzymuje **różnorodność** i pozwala wyjść z optimum lokalnego,
- gwarantuje, że każde rozwiązanie da się teoretycznie osiągnąć.

**Prawdopodobieństwo mutacji `p_m`** jest liczone **na gen**, nie na osobnika. Średnia liczba
zmutowanych genów w osobniku to `p_m · 21`, np. dla `p_m = 0,05` to ok. 1 gen.

**Mutacja przez losowe przypisanie** (*random reset*, użyta w zadaniu, `mutation` w
[ga.py](ga.py)): każdy gen z prawdopodobieństwem `p_m` dostaje nową, losową wartość z
`{0, …, max_i}`. Nowa wartość może przypadkiem równać się starej, wtedy mutacja nic nie zmienia.

Alternatywa: **mutacja „±1”** (*creep mutation*) zmienia gen o jedną porcję w górę lub w dół. Daje
mniejsze, łagodniejsze kroki.

### Sukcesja (strategia zastępowania)

**Sukcesja** decyduje, które osobniki tworzą następne pokolenie.

- **Sukcesja pokoleniowa** (użyta w zadaniu): potomkowie **w całości zastępują** rodziców.
- **Elitaryzm**: kilku najlepszych osobników przechodzi do następnego pokolenia bez zmian. Gwarantuje,
  że najlepszy wynik w populacji nigdy się nie pogorszy. W zadaniu go nie ma, więc najlepszy
  dotąd znaleziony osobnik jest **zapamiętywany osobno** (zmienna `best_chrom` w `run_ga`).
- **Sukcesja (μ + λ)**: rodzice i potomkowie konkurują razem, przeżywają najlepsi.

### Warunek stopu

**Warunek stopu** określa, kiedy algorytm kończy pracę. Możliwości:

- zadana liczba pokoleń (**użyta w zadaniu: 300**),
- zadana liczba ocen funkcji przystosowania,
- brak poprawy przez określoną liczbę pokoleń (stagnacja),
- osiągnięcie zadanej jakości rozwiązania.

### Eksploracja i eksploatacja

- **Eksploracja** to przeszukiwanie nowych, nieznanych obszarów przestrzeni. Zapewnia ją głównie
  **mutacja**.
- **Eksploatacja** to ulepszanie rozwiązań w pobliżu najlepszych znanych. Zapewnia ją głównie
  **selekcja**, a krzyżowanie łączy obie role.

Dobry AG utrzymuje **równowagę** między nimi. Wyniki zadania to dobrze pokazują:

- `p_m = 0,005`: za mało eksploracji, populacja szybko staje się jednorodna,
- `p_m = 0,2`: za dużo eksploracji, dobre rozwiązania są ciągle niszczone,
- `p_m = 0,05`: równowaga i najlepsze wyniki.

### Różnorodność populacji i przedwczesna zbieżność

**Różnorodność** oznacza, jak bardzo osobniki w populacji się od siebie różnią. Gdy wszystkie są
takie same, krzyżowanie nic nie daje (krzyżowanie dwóch identycznych chromosomów daje te same
chromosomy), a postęp zależy tylko od mutacji.

**Przedwczesna zbieżność** to sytuacja, w której populacja traci różnorodność i „zbiega” do jednego
rozwiązania, zanim znajdzie dobre. W zadaniu objawia się tym, że średnie przystosowanie populacji
zrównuje się z najlepszym (wykres [results/population_mean.png](results/population_mean.png) dla
`p_m = 0,005`).

### Zbieżność

**Zbieżność** to stopniowe ustalanie się populacji i najlepszego wyniku. **Krzywa zbieżności**
pokazuje najlepszą (lub średnią) wartość funkcji celu w kolejnych pokoleniach
(wykresy `results/convergence_*.png`).

### Ziarno generatora (seed)

**Ziarno** to liczba startowa generatora liczb pseudolosowych. To samo ziarno daje identyczny ciąg
„losowych” liczb, więc identyczny przebieg AG. Dzięki temu wyniki są **powtarzalne**. W
eksperymentach każda konfiguracja działa z ziarnami 0–9, czyli 10 niezależnymi uruchomieniami.

---

## 3. Pojęcia używane w eksperymentach

### Programowanie całkowitoliczbowe (ILP) i optimum referencyjne

**Programowanie liniowe całkowitoliczbowe** (*Integer Linear Programming*, ILP) to klasa problemów,
w których:

- funkcja celu jest **liniowa** względem zmiennych,
- ograniczenia są **liniowe**,
- zmienne muszą być **całkowite**.

Problem diety spełnia te warunki:

```
minimalizuj   Σ cena_i · x_i
przy          min_j ≤ Σ_i zawartość_ij · x_i ≤ max_j     dla każdego składnika j
              0 ≤ x_i ≤ max_i,   x_i ∈ ℤ
```

Takie problemy rozwiązuje się **dokładnie** metodą **podziału i ograniczeń** (*branch and bound*):
solwer rozwiązuje wersję bez wymogu całkowitości (łatwą), a gdy wynik nie jest całkowity, dzieli
problem na dwa podproblemy (np. `x_i ≤ 1` oraz `x_i ≥ 2`) i odrzuca gałęzie, które nie mogą dać
lepszego wyniku. Na końcu ma **dowód**, że znalezione rozwiązanie jest globalnie optymalne.

W zadaniu używamy `scipy.optimize.milp` (funkcja `exact_optimum` w [ga.py](ga.py)), który daje
**7,70 zł**. Wynik ILP służy **wyłącznie do oceny AG** i nie jest jego częścią.

Dlaczego mimo to stosujemy AG? ILP działa tylko dlatego, że ten problem jest liniowy. AG wymaga
jedynie możliwości ocenienia rozwiązania, więc poradziłby sobie także z nieliniowym celem (np. kara
za monotonię diety, rabaty ilościowe), gdzie ILP nie da się zastosować bezpośrednio.

### Metryki z tabel wyników

| metryka | znaczenie |
|---|---|
| **średnia f** | średnia wartość funkcji celu najlepszego osobnika z 10 uruchomień |
| **odchylenie std** | jak bardzo wyniki różnią się między uruchomieniami (miara stabilności) |
| **min / max** | najlepszy i najgorszy wynik z 10 uruchomień |
| **luka do optimum** | `(średnia f − 7,70) / 7,70`, czyli o ile procent gorzej od optimum |
| **dopuszczalne** | odsetek uruchomień, w których najlepszy osobnik spełnia wszystkie ograniczenia |
| **trafienia opt.** | w ilu uruchomieniach znaleziono dokładnie 7,70 zł |
| **śr. pokolenie best** | w którym pokoleniu średnio znaleziono najlepszego osobnika. Wczesne pokolenie przy słabym wyniku oznacza stagnację |

### Siatka parametrów (grid search)

**Przeszukiwanie siatki** polega na sprawdzeniu wszystkich kombinacji wartości kilku parametrów.
Eksperyment 1 to siatka 5 × 6 = 30 konfiguracji (`p_c` × `p_m`), każda uruchamiana 10 razy, czyli
300 uruchomień.

### Istotność różnic

Gdy różnica średnich dwóch konfiguracji jest mniejsza niż ich odchylenia standardowe, przy 10
uruchomieniach nie można stwierdzić, że jedna jest naprawdę lepsza. Różnica może wynikać z
losowości. Dlatego w wnioskach wpływ `p_c` przy `p_m = 0,05` uznano za nieistotny.

---

## 4. Algorytm krok po kroku na przykładzie

### Pseudokod

```
wczytaj dane, ustaw parametry (N, liczba pokoleń, p_c, p_m, k, seed)
P ← N losowych chromosomów                       # krok 1: inicjalizacja
oceń F dla każdego osobnika w P                  # krok 2: ocena
najlepszy ← najlepszy osobnik w P

dla g = 0, 1, …, G:
    zaktualizuj najlepszego i zapisz statystyki  # krok 3
    jeśli g = G: zakończ                         # krok 4: warunek stopu
    R ← selekcja_turniejowa(P, k)                # krok 5: N rodziców
    D ← krzyżowanie_jednopunktowe(R, p_c)        # krok 6: N potomków
    D ← mutacja(D, p_m)                          # krok 7
    P ← D; oceń F dla każdego osobnika w P       # krok 8: sukcesja i ocena

zwróć najlepszego
```

Odpowiada to funkcji `run_ga` w [ga.py](ga.py).

Żeby przykład był czytelny, poniżej użyto **miniaturowej populacji N = 4** (ziarno 42). Prawdziwe
uruchomienia mają N = 20 i więcej, ale każdy krok działa identycznie.

### Krok 1: inicjalizacja

Każdy gen każdego osobnika jest losowany niezależnie z `{0, …, max_i}`
(`DietProblem.random_population`):

```
osobnik 0: [0, 3, 1, 1, 1, 2, 0, 2, 0, 0, 1, 1, 2, 2, 2, 3, 1, 0, 2, 1, 2]
osobnik 1: [1, 0, 2, 2, 2, 1, 2, 1, 1, 1, 0, 0, 1, 2, 0, 3, 2, 0, 1, 0, 3]
osobnik 2: [2, 1, 0, 2, 1, 2, 2, 2, 2, 0, 0, 0, 1, 0, 1, 0, 2, 2, 2, 2, 1]
osobnik 3: [2, 1, 0, 2, 1, 0, 1, 2, 0, 1, 0, 1, 1, 0, 0, 2, 2, 2, 1, 0, 3]
```

Losowe jadłospisy zawierają średnio ok. połowy maksymalnej liczby porcji każdego produktu, więc są
zdecydowanie **za duże** (ok. 4000 kcal) i za drogie.

### Krok 2: ocena

Dla każdego osobnika liczymy wartości odżywcze, koszt, naruszenie `V`, funkcję celu `f` i
przystosowanie `F`.

| osobnik | kcal | białko | tłuszcz | węgl. | błonnik | koszt | V | f | F |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 4055 | 239,9 | 102,1 | 554,0 | 81,1 | 38,50 | 2,0654 | 451,58 | 0,00221 |
| 1 | 3989 | 170,5 | 96,2 | 623,9 | 58,8 | 25,20 | 1,3720 | 299,59 | **0,00333** |
| 2 | 4305 | 257,5 | 161,7 | 459,4 | 56,8 | 33,40 | 2,3370 | 500,80 | 0,00199 |
| 3 | 3974 | 168,2 | 131,4 | 539,7 | 72,8 | 23,40 | 1,7344 | 370,29 | 0,00269 |

Szczegółowo dla osobnika 0: wszystkie składniki są **powyżej** górnej granicy, więc:

```
kcal:    (4055 − 2500) / 2500 = 0,6220
białko:  (239,9 − 160) / 160  = 0,4994
tłuszcz: (102,1 − 90) / 90    = 0,1344
węgl.:   (554,0 − 380) / 380  = 0,4579
błonnik: (81,1 − 60) / 60     = 0,3517
                          V   = 2,0654
f = 38,50 + 200 · 2,0654 = 451,58 zł
F = 1 / (1 + 451,58)     = 0,00221
```

Na początku kara całkowicie dominuje nad kosztem. Algorytm najpierw uczy się więc **spełniać
ograniczenia**, a dopiero potem **obniżać koszt**.

Najlepszy w populacji jest osobnik 1 (największe `F`), więc zostaje zapamiętany jako „najlepszy
dotąd”.

### Krok 3: aktualizacja najlepszego i statystyki

W każdym pokoleniu algorytm zapisuje:

- najlepsze `F` w bieżącej populacji (`history_best`),
- średnie `F` populacji (`history_mean`),
- najlepsze `F` znalezione do tej pory (`history_best_so_far`).

Jeśli najlepszy osobnik bieżącej populacji jest lepszy od zapamiętanego, zastępuje go (razem z
numerem pokolenia). Z tych danych powstają wykresy zbieżności.

### Krok 4: warunek stopu

Jeśli osiągnięto zadaną liczbę pokoleń (300), algorytm kończy i zwraca zapamiętanego najlepszego
osobnika. W przeciwnym razie przechodzi do tworzenia nowego pokolenia.

### Krok 5: selekcja turniejowa (k = 3)

Rozgrywamy N = 4 turnieje. W każdym losujemy 3 numery osobników (mogą się powtarzać) i wybieramy
tego z największym `F`:

| turniej | uczestnicy | ich F | zwycięzca |
|---|---|---|---|
| 1 | 2, 2, 0 | 0,00199; 0,00199; 0,00221 | **0** |
| 2 | 1, 3, 3 | 0,00333; 0,00269; 0,00269 | **1** |
| 3 | 1, 3, 3 | 0,00333; 0,00269; 0,00269 | **1** |
| 4 | 1, 3, 1 | 0,00333; 0,00269; 0,00333 | **1** |

Pula rodziców: `[0, 1, 1, 1]`.

Widać presję selekcyjną: najlepszy osobnik 1 został wybrany 3 razy, najgorszy osobnik 2 ani razu.
Osobnik 0 (drugi od końca) przeszedł, bo trafił na słabszego rywala, co pokazuje, że słabsze
osobniki też mają szansę.

### Krok 6: krzyżowanie jednopunktowe

Rodzice są łączeni w pary kolejno: (pierwszy, drugi), (trzeci, czwarty). Dla każdej pary losujemy
liczbę z [0, 1). Jeśli jest mniejsza od `p_c`, para jest krzyżowana.

Przykład krzyżowania osobników 3 (A) i 1 (B) z punktem cięcia `cut = 11`:

```
                 0  1  2  3  4  5  6  7  8  9 10 | 11 12 13 14 15 16 17 18 19 20
rodzic A (3):  [ 2, 1, 0, 2, 1, 0, 1, 2, 0, 1, 0 |  1, 1, 0, 0, 2, 2, 2, 1, 0, 3 ]
rodzic B (1):  [ 1, 0, 2, 2, 2, 1, 2, 1, 1, 1, 0 |  0, 1, 2, 0, 3, 2, 0, 1, 0, 3 ]

dziecko 1:     [ 2, 1, 0, 2, 1, 0, 1, 2, 0, 1, 0 |  0, 1, 2, 0, 3, 2, 0, 1, 0, 3 ]
dziecko 2:     [ 1, 0, 2, 2, 2, 1, 2, 1, 1, 1, 0 |  1, 1, 0, 0, 2, 2, 2, 1, 0, 3 ]
```

| | koszt | V | f | F |
|---|---|---|---|---|
| rodzic A (3) | 23,40 | 1,7344 | 370,29 | 0,00269 |
| rodzic B (1) | 25,20 | 1,3720 | 299,59 | 0,00333 |
| **dziecko 1** | 20,10 | 0,9504 | **210,18** | **0,00474** |
| dziecko 2 | 28,50 | 2,2704 | 482,58 | 0,00207 |

Dziecko 1 jest **lepsze od obu rodziców**: wzięło „lżejszą” część z każdego z nich (m.in. bez
soczewicy i orzechów włoskich). Dziecko 2 dostało cięższe części i jest gorsze. Tak działa
krzyżowanie: nie gwarantuje poprawy, ale tworzy nowe kombinacje, a selekcja w kolejnych pokoleniach
zatrzyma te lepsze.

### Krok 7: mutacja

Dla każdego genu każdego potomka losujemy liczbę z [0, 1). Jeśli jest mniejsza od `p_m`, gen
dostaje nową losową wartość z `{0, …, max_i}`.

Przykład: w dziecku 2 mutuje gen 17 (orzechy włoskie, max = 2), nowa wartość to 0:

```
przed: [1, 0, 2, 2, 2, 1, 2, 1, 1, 1, 0, 1, 1, 0, 0, 2, 2, 2, 1, 0, 3]
po:    [1, 0, 2, 2, 2, 1, 2, 1, 1, 1, 0, 1, 1, 0, 0, 2, 2, 0, 1, 0, 3]
                                                          ↑
```

| | kcal | tłuszcz | koszt | f |
|---|---|---|---|---|
| przed | 4514 | 135,8 | 28,50 | 482,58 |
| po | 4124 | 96,8 | 24,90 | **340,98** |

Usunięcie dwóch porcji orzechów (390 kcal, 39 g tłuszczu) zbliżyło jadłospis do zakresów. Mutacja
może też pogorszyć osobnika: wtedy selekcja po prostu rzadziej wybierze go na rodzica.

Przy `p_m = 0,05` i 21 genach:

- średnio ok. 1 gen na osobnika jest mutowany,
- prawdopodobieństwo, że osobnik nie zostanie zmieniony wcale, to `0,95^21 ≈ 34%`.

### Krok 8: sukcesja pokoleniowa i ponowna ocena

Potomkowie po krzyżowaniu i mutacji **zastępują całą starą populację**. Liczymy dla nich `F` i
wracamy do kroku 3.

Ponieważ nie ma elitaryzmu, najlepszy osobnik może w tym kroku zniknąć (np. gdy nie wygra żadnego
turnieju albo jego potomek zostanie zepsuty przez mutację). Właśnie dlatego krok 3 zapamiętuje
go osobno.

---

## 5. Przebieg całego uruchomienia

Prawdziwe uruchomienie: N = 20, 300 pokoleń, `p_c = 0,8`, `p_m = 0,05`, ziarno 5
(`python main.py --pop 20 --gen 300 --pc 0.8 --pm 0.05 --seed 5`). Wartości funkcji celu `f`
w złotówkach:

| pokolenie | najlepszy w populacji | średnia populacji | najlepszy dotąd |
|---|---|---|---|
| 0 | 72,02 | 196,91 | 72,02 |
| 1 | 47,70 | 120,77 | 47,70 |
| 5 | 15,90 | 32,82 | 15,90 |
| 10 | 14,90 | 24,33 | 14,90 |
| 25 | 14,40 | 30,72 | 14,30 |
| 50 | 13,30 | 21,35 | 10,80 |
| 100 | 9,90 | 18,52 | 8,80 |
| 200 | 9,30 | 13,95 | 8,80 |
| 300 | 10,40 | 15,20 | **8,40** (pokolenie 210) |

Co widać:

1. **Pokolenia 0–10: szybka poprawa.** Losowe jadłospisy łamią ograniczenia, więc różnice w karze
   są ogromne i selekcja szybko usuwa najgorszych. Funkcja celu spada z ok. 200 do ok. 25 zł.
2. **Pokolenia 10–100: dopracowywanie.** Populacja jest już blisko zbioru dopuszczalnego, a postęp
   polega na wymianie droższych produktów na tańsze. Kolejne poprawy są coraz mniejsze.
3. **Pokolenia 100–300: stagnacja.** Najlepszy dotąd poprawia się rzadko (8,80 → 8,40 zł).
4. **Brak elitaryzmu.** W pokoleniu 300 najlepszy w populacji ma 10,40 zł, gorzej niż zapamiętane
   8,40 zł. Dobre rozwiązanie zostało zgubione przez mutację, ale nie przepadło, bo zostało
   zapisane.
5. **Średnia populacji jest wyraźnie gorsza od najlepszego** (15,20 vs 10,40 zł). To efekt
   mutacji: część potomków w każdym pokoleniu zostaje „popsuta”, co utrzymuje różnorodność.

Wynik 8,40 zł jest o 9% gorszy od optimum (7,70 zł). Znaleziony jadłospis:

```
2 × płatki owsiane, 1 × chleb pełnoziarnisty, 2 × makaron,
1 × soczewica, 1 × masło orzechowe, 3 × oliwa z oliwek
```

Różni się od optimum tylko trzema genami (chleb +1, masło orzechowe −1, oliwa +1). To typowe
**optimum lokalne**: żadna zmiana jednego genu nie daje lepszego dopuszczalnego jadłospisu, a do
optimum trzeba zmienić kilka genów naraz.

---

## 6. Dlaczego to w ogóle działa

### Intuicja

- **Selekcja** sprawia, że cechy dobrych rozwiązań (np. „dużo płatków owsianych, bo są tanim
  źródłem kalorii”) rozprzestrzeniają się w populacji.
- **Krzyżowanie** łączy dobre fragmenty z różnych osobników, np. dobrą część „zbożową” od jednego
  rodzica i dobrą część „tłuszczową” od drugiego.
- **Mutacja** sprawdza zmiany, których nie ma w populacji, i nie dopuszcza do całkowitej utraty
  różnorodności.

### Twierdzenie o schematach i hipoteza bloków budujących

Klasyczne uzasadnienie AG (Holland, Goldberg):

- **Schemat** to wzorzec chromosomu z ustalonymi niektórymi genami, np. `[2, *, *, 2, *, …]`
  („2 porcje płatków i 2 porcje makaronu, reszta dowolna”).
- **Twierdzenie o schematach** mówi, że krótkie schematy o niskim rzędzie (mało ustalonych genów,
  blisko siebie) i ponadprzeciętnym przystosowaniu otrzymują w kolejnych pokoleniach wykładniczo
  rosnącą liczbę kopii.
- **Hipoteza bloków budujących** mówi, że AG składa dobre rozwiązanie z takich krótkich, dobrych
  fragmentów („bloków”) za pomocą krzyżowania.

W praktyce to tłumaczy, dlaczego **kolejność genów ma znaczenie** przy krzyżowaniu jednopunktowym:
geny leżące blisko siebie rzadziej są rozdzielane przez punkt cięcia. W zadaniu produkty są
pogrupowane mniej więcej tematycznie (zboża, białko, warzywa, owoce, tłuszcze), co sprzyja
zachowywaniu takich bloków.

### Ograniczenia AG

- **Brak gwarancji optimum**: przy N = 20 żadne z 300 uruchomień nie trafiło w 7,70 zł.
- **Wrażliwość na parametry**: `p_m = 0,005` daje średnio 19,6 zł, a `p_m = 0,05` daje 10,5 zł
  przy tych samych pozostałych ustawieniach.
- **Losowość wyników**: trzeba wykonywać wiele uruchomień i analizować statystyki, a nie jeden
  wynik.
- **Koszt obliczeniowy rośnie z N**: większa populacja daje lepsze wyniki, ale wymaga
  proporcjonalnie więcej ocen funkcji przystosowania.
