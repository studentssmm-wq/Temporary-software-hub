export interface TarotCard {
  id: number;
  name: string;
  image: string;
  meaning: string;
  reversedMeaning: string;
}

export interface DrawnCard {
  card: TarotCard;
  isReversed: boolean;
  position?: string;
}

export interface SpreadRecord {
  id: string;
  question: string;
  createdAt: number;
  cards: DrawnCard[];
}

export type Page = "home" | "spread" | "daily" | "cards" | "history";
