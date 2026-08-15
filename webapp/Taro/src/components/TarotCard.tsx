import React from "react";
import type { DrawnCard } from "../types/tarot";

interface Props {
  drawnCard?: DrawnCard;
  isRevealed: boolean;
  onClick?: () => void;
}

export const TarotCard: React.FC<Props> = ({
  drawnCard,
  isRevealed,
  onClick,
}) => {
  return (
    <div className="card-container" onClick={onClick}>
      <div className={`card-inner ${isRevealed ? "revealed" : ""}`}>
        <div className="card-face card-back">
          <span style={{ fontSize: "2rem" }}>🔮</span>
        </div>
        <div
          className={`card-face card-front ${drawnCard?.isReversed ? "reversed" : ""}`}
        >
          {drawnCard && (
            <>
              <div style={{ flex: 1, display: "flex", alignItems: "center" }}>
                <span style={{ fontSize: "3rem" }}>🃏</span>{" "}
                {/* Placeholder for actual image */}
              </div>
              <div className="card-title">{drawnCard.card.name}</div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
