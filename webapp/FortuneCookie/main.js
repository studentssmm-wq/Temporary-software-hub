if (window.Telegram && window.Telegram.WebApp) {
  window.Telegram.WebApp.ready();
  window.Telegram.WebApp.expand(); // Розгортає Web App на весь екран
}

const open = document.querySelector("#open");
const btn = document.querySelector("#btn");
const screenOne = document.querySelector(".screenOne");
const screenTwo = document.querySelector(".screenTwo");

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

// Eventos
open.addEventListener("click", firstClick);

btn.addEventListener("click", Click);

// Funções

function firstClick() {
  Click();
  pickFortune();
}

function Click() {
  // Pego no documento a classe "screenOne" e adiciono/removo "hide";
  screenOne.classList.toggle("hide");
  // Pego no documento a classe "screenTwo" e removo/adiciono "hide";
  screenTwo.classList.toggle("hide");
}

function pickFortune() {
  let allFortunes = fortune.length;
  let randomNumber = Math.floor(Math.random() * allFortunes);
  screenTwo.querySelector("h2").innerText = `${fortune[randomNumber]}`;
}
