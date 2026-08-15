const API_BASE = "https://temporary-software-hub.onrender.com/api/webapp";
let initData = "";

// Ініціалізація Telegram Web App
if (window.Telegram && window.Telegram.WebApp) {
  window.Telegram.WebApp.ready();
  window.Telegram.WebApp.expand();
  initData = window.Telegram.WebApp.initData;
}

// Елементи інтерфейсу
const openBtn = document.querySelector("#open");
const resetBtn = document.querySelector("#btn");
const screenOne = document.querySelector(".screenOne");
const screenTwo = document.querySelector(".screenTwo");
const balanceDisplay = document.querySelector("#balanceDisplay");

// Масив передбачень
const fortune = [
  "Успіх — це подорож, а не пункт призначення.",
  "Великі мрії починаються з малих дій.",
  "Можливості з'являються тоді, коли ми чекаємо на них найменше.",
  "Повір у себе, і все стане можливим.",
  "Знання — це скарб розуму.",
  "Не бійся помилятися, це частина процесу навчання.",
  "Час лікує всі рани.",
  "Позитивне мислення приваблює позитивні події.",
  "Вір у свої мрії та йди вперед.",
  "Труднощі — це замасковані можливості.",
  "Життя — це пригода, насолоджуйся кожною миттю.",
  "Любов — це ключ до щастя.",
  "Будь тією зміною, яку хочеш бачити у світі.",
  "Ти здатний досягти всього, чого побажаєш.",
  "Удача завжди на боці тих, хто наполегливо працює.",
  "Успіх — це результат наполегливості та відданості своїй справі.",
  "Справжнє щастя йде зсередини.",
  "Вдячність — це ключ до повноцінного життя.",
  "Ти унікальний і особливий, цінуй свою індивідуальність.",
  "Світ відкритий для тебе — іди та підкорюй його!",
];

// --- Взаємодія з сервером ---

// 1. Завантаження балансу
function loadBalance() {
  if (!initData) return;

  fetch(`${API_BASE}/user`, {
    method: "GET",
    headers: {
      Authorization: `tma ${initData}`,
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.coins !== undefined) {
        balanceDisplay.innerText = `${data.coins} 🦝`;
      }
    })
    .catch((error) => console.error("Помилка завантаження балансу:", error));
}

// 2. Спроба відкрити печиво (списання токенів)
function handleCookieClick() {
  // Блокуємо кнопку, щоб уникнути подвійних кліків
  openBtn.disabled = true;
  openBtn.style.opacity = "0.7";

  fetch(`${API_BASE}/spend`, {
    method: "POST",
    headers: {
      Authorization: `tma ${initData}`,
      "Content-Type": "application/json",
    },
    // Списуємо 1 токен за використання
    body: JSON.stringify({ amount: 1, feature: "fortune_cookie" }),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Недостатньо коштів");
      }
      return response.json();
    })
    .then((data) => {
      // Якщо успішно: оновлюємо баланс і відкриваємо печиво
      loadBalance();
      openCookie();
    })
    .catch((error) => {
      // Якщо токенів немає або сталася помилка
      alert(
        "У вас недостатньо Єнот-токенів! 😢 Поповніть баланс у профілі бота.",
      );
    })
    .finally(() => {
      // Розблоковуємо кнопку
      openBtn.disabled = false;
      openBtn.style.opacity = "1";
    });
}

// --- Логіка інтерфейсу ---

function openCookie() {
  screenOne.classList.add("hide");
  screenTwo.classList.remove("hide");
  pickFortune();
}

function resetApp() {
  screenOne.classList.remove("hide");
  screenTwo.classList.add("hide");
}

function pickFortune() {
  let allFortunes = fortune.length;
  let randomNumber = Math.floor(Math.random() * allFortunes);
  screenTwo.querySelector("h2").innerText = `${fortune[randomNumber]}`;
}

// Додаємо слухачі подій
openBtn.addEventListener("click", handleCookieClick);
resetBtn.addEventListener("click", resetApp);

// Завантажуємо баланс при старті
loadBalance();
