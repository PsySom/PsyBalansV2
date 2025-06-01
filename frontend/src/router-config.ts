// src/router-config.ts
// Конфигурация флагов для будущей версии React Router v7

import { future } from "react-router-dom";

// Применяем будущие флаги
export const routerFutureConfig = {
  ...future,
  v7_startTransition: true,
  v7_relativeSplatPath: true
};