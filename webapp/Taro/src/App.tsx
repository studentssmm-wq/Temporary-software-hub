import React, { useState, useEffect } from "react";
import type { Page } from "./types/tarot";
import { HomePage } from "./pages/HomePage";
import { SpreadPage } from "./pages/SpreadPage";
// import { DailyPage, CardsPage, HistoryPage } from './pages/...'; (заглушки)

export const App: React.FC = () => {
  const [page, setPage] = useState<Page>("home");

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    tg?.ready();
    tg?.expand();
  }, []);

  return (
    <>
      {page === "home" && <HomePage setPage={setPage} />}
      {page === "spread" && <SpreadPage />}
      {/* Інші сторінки рендеряться аналогічно */}

      <div className="bottom-nav">
        <button
          className={`nav-item ${page === "home" ? "active" : ""}`}
          onClick={() => setPage("home")}
        >
          <span className="nav-icon">🏠</span>
          <span>Головна</span>
        </button>
        <button
          className={`nav-item ${page === "spread" ? "active" : ""}`}
          onClick={() => setPage("spread")}
        >
          <span className="nav-icon">🔮</span>
          <span>Розклад</span>
        </button>
        <button
          className={`nav-item ${page === "cards" ? "active" : ""}`}
          onClick={() => setPage("cards")}
        >
          <span className="nav-icon">🃏</span>
          <span>Карти</span>
        </button>
        <button
          className={`nav-item ${page === "history" ? "active" : ""}`}
          onClick={() => setPage("history")}
        >
          <span className="nav-icon">📖</span>
          <span>Історія</span>
        </button>
      </div>
    </>
  );
};

export default App;
