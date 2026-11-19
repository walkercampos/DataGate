import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";
import { setFuso } from "../lib/datas";

beforeEach(() => {
  localStorage.clear();
  window.location.hash = "";
  setFuso("America/Sao_Paulo");
});
afterEach(() => cleanup());
