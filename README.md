# Pub Manager
## Backend
Backend napisany jest w języku programowania Python w oparciu o framework Flask umożliwiający stworzenie serwera. Warstwa backendowa pozwala na komunikację pomiędzy interfejsem użytkownika a bazą danych.

## Baza danych

![image](https://github.com/RafalG1991/projekt_pub/assets/92755273/8e99174e-ff6a-46a6-93f6-db26ae09ae31)


## Struktura
Struktura backendu została oparta o strukturę model/router/kontroler. Poszczególne klasy odpowiadają za konkretne tabele bazy danych oraz utworzone na ich potrzeby obiekty. Zawierają także kontrolery - metody, które pozwalają na dokonywanie operacji na konkretnych obiektach.
Aplikacja serwerowa podzielona jest na następujące klasy i dostępne w nich metody:
### Lounge – odpowiadającą za obsługę stolików:
- get_tables - uzyskiwanie listy wszystkich stolików,
- getAvailableTables - filtrowanie stolików po liczbie dostępnych miejsc,

### Orders – odpowiadającą za obsługę zamówień: 
- openOrder - tworzenie nowego zamówienia,
- show_order - pobieranie danych o zamówieniu,
- closeOrder – zamykanie zamówienia,
- list_menu – wyświetlanie menu dostępnych drinków,
- show_opened_orders – wyświetlanie otwartych zamówień,
- add_product – dodawanie drinków do zamówienia oraz zaktualizowanie danych magazynowych na temat ilości składników, metoda posiada walidację ilości dostępnych składników i zwraca błąd gdy ich ilość jest niewystarczająca do sporządzenia napoju

### Reports – odpowiadającą za obsługę raportów kasowych i magazynowych:
- orders_report – wyświetlanie listy wszystkich zamówień
- inventory_report – wyświetlanie listy składników wraz z ich stanem magazynowym
- add_ingredient – dodawanie składników do stanu magazynowego


##API
### Lounge
#### `GET /lounge`
<p> 
  Pobieranie listy wszystkich stolików w Pubie
</p>

### Lounge
#### `GET /lounge/available/<int:id>`
<p> 
  Pobieranie listy dostępnych stolików w Pubie o zadanej pojemności
</p>

### Orders
#### `POST /order/open`
<p> 
  Utworzenie nowego zamówienia. 
</p>
<p>
Przyjmuje dane w formacie JSON o strukturze:

```javascript
{
  " tableNumber": int,
  " customersNumber": int
}
```
</p>

#### `POST /order/close`
<p> 
  Zamyka wskazane zamówienie.
</p>
<p>
Przyjmuje dane w formacie JSON o strukturze:

```javascript
{
  " tableNumber": int
}
```
</p>

#### `GET /order/menu`
<p> 
  Pobiera listę menu drinków dostępnych w Pubie
</p>

#### `GET /order/show/<int:table>`
<p> 
  Pobiera szczegóły zamówienia o wskazanym numerze ID
</p>

#### `POST /order/add`
<p> 
 Dodaje drink do zamówienia.
</p>
<p>
Przyjmuje dane w formacie JSON o strukturze:

```javascript
{
  "id": int,
  "choice": string,
  "quantity": int
}
```
</p>

### Reports
#### `GET /report/inventory`
<p> 
 Pobieranie listy wszystkich składników
</p>

#### `GET /report/orders`
<p> 
 Pobieranie listy wszystkich zamówień
</p>

#### `POST /report/add`
<p> 
 Dodaje ilość składnika do stanu magazynowego.
</p>
<p>
Przyjmuje dane w formacie JSON o strukturze:

```javascript
{
  "id": int,
  "quantity": int
}
```
</p>
