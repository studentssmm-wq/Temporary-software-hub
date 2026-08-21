// Ініціалізація Telegram Web App
if (window.Telegram && window.Telegram.WebApp) {
  window.Telegram.WebApp.ready();
  window.Telegram.WebApp.expand();
}

// Елементи інтерфейсу
const openBtn = document.querySelector("#open");
const resetBtn = document.querySelector("#btn");
const screenOne = document.querySelector(".screenOne");
const screenTwo = document.querySelector(".screenTwo");

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
  const randomNumber = Math.floor(Math.random() * fortune.length);
  screenTwo.querySelector("h2").innerText = fortune[randomNumber];
}

// Додаємо слухачі подій
openBtn.addEventListener("click", openCookie);
resetBtn.addEventListener("click", resetApp);
