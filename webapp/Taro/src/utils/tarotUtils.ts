import { tarotCards } from "../data/tarotCards";
import type { DrawnCard, SpreadRecord } from "../types/tarot";

export const getRandomCards = (count: number): DrawnCard[] => {
  const shuffled = [...tarotCards].sort(() => 0.5 - Math.random());
  return shuffled.slice(0, count).map((card) => ({
    card,
    isReversed: Math.random() < 0.25, // 25% chance
  }));
};

export const getDailyCard = (): DrawnCard | null => {
  const today = new Date().toISOString().split("T")[0];
  const saved = localStorage.getItem("dailyCard");
  if (saved) {
    const parsed = JSON.parse(saved);
    if (parsed.date === today) return parsed.card;
  }
  return null;
};

export const drawDailyCard = (): DrawnCard => {
  const card = getRandomCards(1)[0];
  const today = new Date().toISOString().split("T")[0];
  localStorage.setItem("dailyCard", JSON.stringify({ date: today, card }));
  return card;
};

export const saveSpread = (question: string, cards: DrawnCard[]) => {
  const newSpread: SpreadRecord = {
    id: Date.now().toString(),
    question,
    createdAt: Date.now(),
    cards,
  };
  const history = getHistory();
  history.unshift(newSpread);
  if (history.length > 10) history.pop();
  localStorage.setItem("tarotHistory", JSON.stringify(history));
};

export const getHistory = (): SpreadRecord[] => {
  const saved = localStorage.getItem("tarotHistory");
  return saved ? JSON.parse(saved) : [];
};
