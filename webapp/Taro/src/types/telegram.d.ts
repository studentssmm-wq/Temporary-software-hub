declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        ready: () => void;
        expand: () => void;
        initData: string;
        initDataUnsafe: {
          user?: {
            first_name: string;
            last_name?: string;
            username?: string;
            id: number;
          };
        };
      };
    };
  }
}
export {};
