import React from "react";
import type { Page } from "../types/tarot";

interface Props {
  setPage: (page: Page) => void;
}

export const HomePage: React.FC<Props> = ({ setPage }) => {
  const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
  const firstName = tgUser?.first_name || "Мандрівник";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        marginTop: "2rem",
      }}
    >
      <h1>TAROT</h1>
      <p style={{ marginBottom: "2rem" }}>Привіт, {firstName} ✨</p>

      <p style={{ marginBottom: "1.5rem", color: "var(--text)" }}>
        Дізнайся, що підказують карти
      </p>

      <button className="btn" onClick={() => setPage("daily")}>
        🃏 Карта дня
      </button>
      <button className="btn primary" onClick={() => setPage("spread")}>
        🔮 Розклад на 3 карти
      </button>
      <button className="btn" onClick={() => setPage("cards")}>
        📖 Значення карт
      </button>
    </div>
  );
};
