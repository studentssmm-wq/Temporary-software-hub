import { useState, useEffect } from "react";
import "./App.css";

const API_BASE = "https://temporary-software-hub.onrender.com/api/webapp";

const FORTUNES = [
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

function App() {
  const [currentScreen, setCurrentScreen] = useState("hub"); // 'hub', 'cookie', 'tarot'
  const [balance, setBalance] = useState("⏳");

  const fetchBalance = (dataStr) => {
    fetch(`${API_BASE}/user`, {
      method: "GET",
      headers: {
        Authorization: `tma ${dataStr}`,
        "Content-Type": "application/json",
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.coins !== undefined) setBalance(data.coins);
      })
      .catch((err) => console.error("Помилка завантаження балансу:", err));
  };

  // Ініціалізація Telegram та завантаження балансу
  useEffect(() => {
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();

      const data = window.Telegram.WebApp.initData;

      if (data) {
        fetchBalance(data);
      }
    }
  }, []);

  return (
    <div className="app-container">
      {/* Плашка балансу */}
      <div className="balance-display">Баланс: {balance} 🦝</div>

      {/* ЕКРАН 1: ГОЛОВНИЙ ХАБ */}
      {currentScreen === "hub" && (
        <div className="screen hubScreen">
          <h1>🎮 Ігровий Хаб</h1>
          <p>Обери гру та випробуй вдачу:</p>
          <button
            className="hub-btn"
            onClick={() => setCurrentScreen("cookie")}
          >
            🥠 Печиво з передбаченням
          </button>
          <button
            className="hub-btn tarot-btn"
            onClick={() => setCurrentScreen("tarot")}
          >
            🃏 Карти Таро (Скоро)
          </button>
        </div>
      )}

      {/* ЕКРАН 2: ПЕЧИВО З ПЕРЕДБАЧЕННЯМ */}
      {currentScreen === "cookie" && (
        <CookieGame goBack={() => setCurrentScreen("hub")} />
      )}

      {/* ЕКРАН 3: ТАРО (Заглушка) */}
      {currentScreen === "tarot" && (
        <div className="screen tarotScreen">
          <h1>🃏 Карти Таро</h1>
          <p>
            Ця гра наразі розробляється.
            <br />
            Повертайтеся сюди трішки пізніше!
          </p>
          <button className="back-btn" onClick={() => setCurrentScreen("hub")}>
            🔙 Назад до меню
          </button>
        </div>
      )}
    </div>
  );
}

// === КОМПОНЕНТ ГРИ "ПЕЧИВО" ===
function CookieGame({ goBack }) {
  const [cookieState, setCookieState] = useState("closed"); // 'closed', 'opened'
  const [fortuneText, setFortuneText] = useState("");

  const handleOpenCookie = () => {
    const randomPhrase = FORTUNES[Math.floor(Math.random() * FORTUNES.length)];
    setFortuneText(randomPhrase);
    setCookieState("opened");
  };

  return (
    <div className="screen cookieScreen">
      {cookieState !== "opened" ? (
        <>
          <h1>Яке передбачення чекає на тебе сьогодні?</h1>
          <p>Розкриши печиво та дізнайся!</p>
          <button className="cookie-btn" onClick={handleOpenCookie}>
            <img src="/images/fortune-cookie.png" alt="Печиво" />
          </button>
          <button className="back-btn" onClick={goBack}>
            🔙 Назад до меню
          </button>
        </>
      ) : (
        <>
          <h1>
            Твоє передбачення <br /> на сьогодні:
          </h1>
          <h2 className="fortune-box">{fortuneText}</h2>
          <img
            className="opened-img"
            src="/images/opened-cookie.png"
            alt="Відкрите печиво"
          />
          <button className="hub-btn" onClick={() => setCookieState("closed")}>
            Відкрити інше печиво
          </button>
          <button className="back-btn" onClick={goBack}>
            🔙 Назад до меню
          </button>
        </>
      )}
    </div>
  );
}

export default App;
