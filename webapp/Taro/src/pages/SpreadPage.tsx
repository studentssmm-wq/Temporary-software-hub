import React, { useState } from "react";
import { TarotCard } from "../components/TarotCard";
import type { DrawnCard } from "../types/tarot";
import { getRandomCards, saveSpread } from "../utils/tarotUtils";

export const SpreadPage: React.FC = () => {
  const [question, setQuestion] = useState("");
  const [cards, setCards] = useState<DrawnCard[]>([]);
  const [revealedIdx, setRevealedIdx] = useState<number>(-1);
  const positions = ["Минуле", "Теперішнє", "Майбутнє"];

  const handleDraw = () => {
    if (!question.trim()) return;
    const drawn = getRandomCards(3).map((c, i) => ({
      ...c,
      position: positions[i],
    }));
    setCards(drawn);
    setRevealedIdx(-1);
  };

  const handleReveal = (index: number) => {
    if (index === revealedIdx + 1) {
      setRevealedIdx(index);
      if (index === 2) {
        saveSpread(question, cards); // Зберігаємо, коли всі відкриті
      }
    }
  };

  if (cards.length === 0) {
    return (
      <div>
        <h2>Сформулюй питання</h2>
        <input
          type="text"
          className="text-input"
          placeholder="Введіть своє питання..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button className="btn primary" onClick={handleDraw}>
          Витягнути карти
        </button>
      </div>
    );
  }

  return (
    <div>
      <h2>Ваш розклад</h2>
      <p
        style={{
          textAlign: "center",
          marginBottom: "1rem",
          color: "var(--text)",
        }}
      >
        "{question}"
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
        {cards.map((card, idx) => {
          const isRevealed = idx <= revealedIdx;
          return (
            <div
              key={idx}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <h3 style={{ fontSize: "1rem", color: "var(--muted)" }}>
                {card.position}
              </h3>
              <TarotCard
                drawnCard={card}
                isRevealed={isRevealed}
                onClick={() => handleReveal(idx)}
              />
              {isRevealed && (
                <div style={{ marginTop: "1rem", textAlign: "center" }}>
                  <p style={{ color: "var(--accent)", fontWeight: "bold" }}>
                    {card.card.name} {card.isReversed ? "(Перевернута)" : ""}
                  </p>
                  <p>
                    {card.isReversed
                      ? card.card.reversedMeaning
                      : card.card.meaning}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
