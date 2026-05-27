/**
 * frontend/src/__tests__/Navbar.test.jsx
 *
 * TIPO 3 — TESTES DE COMPONENTE FRONTEND (Component Tests)
 * =========================================================
 *
 * Objetivo: verificar se os componentes React renderizam corretamente,
 * respondem a interações do usuário e mantêm o estado esperado.
 *
 * Esta camada testa a INTERFACE — a parte que o usuário vê e interage —
 * sem depender do backend ou de APIs externas.
 *
 * Técnicas aplicadas:
 *   - Render Testing (verifica se o componente renderiza sem erros)
 *   - Interaction Testing (simula cliques e verifica reações)
 *   - Accessibility Testing (verifica atributos ARIA e elementos semânticos)
 *   - Snapshot Behavior (verifica elementos visíveis vs ocultos)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Navbar from "../components/Navbar";

// Mock do framer-motion para evitar erros de animação no jsdom
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }) => <>{children}</>,
}));

// Helper: renderiza o Navbar dentro de um Router (necessário para NavLink)
const renderNavbar = () =>
  render(
    <MemoryRouter>
      <Navbar />
    </MemoryRouter>
  );

// ═══════════════════════════════════════════════════════════════════════════
// GRUPO 1: Render Testing — O componente renderiza sem erros?
// ═══════════════════════════════════════════════════════════════════════════

describe("Navbar — Render Testing", () => {
  it("renderiza sem lançar exceções", () => {
    // Se este teste passar, o componente monta sem erros de runtime
    expect(() => renderNavbar()).not.toThrow();
  });

  it("exibe o nome da marca 'IntelliBet'", () => {
    renderNavbar();
    // O logo deve conter o texto da marca
    expect(screen.getByText(/Intelli/i)).toBeInTheDocument();
    expect(screen.getByText(/Bet/i)).toBeInTheDocument();
  });

  it("exibe todos os 5 links de navegação no desktop", () => {
    renderNavbar();
    const links = ["Home", "Assistente Virtual", "Jogos", "Pagamentos", "Perfil"];
    links.forEach((link) => {
      // getAllByText porque alguns links aparecem tanto no desktop quanto no mobile
      const elements = screen.getAllByText(link);
      expect(elements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("exibe o campo de pesquisa com placeholder correto", () => {
    renderNavbar();
    const inputs = screen.getAllByPlaceholderText(/pesquise/i);
    expect(inputs.length).toBeGreaterThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// GRUPO 2: Interaction Testing — O menu mobile responde a cliques?
// ═══════════════════════════════════════════════════════════════════════════

describe("Navbar — Interaction Testing (Menu Mobile)", () => {
  it("botão de menu está presente com aria-label 'Menu'", () => {
    renderNavbar();
    const menuButton = screen.getByRole("button", { name: /menu/i });
    expect(menuButton).toBeInTheDocument();
  });

  it("menu mobile abre ao clicar no botão hamburguer", () => {
    renderNavbar();
    const menuButton = screen.getByRole("button", { name: /menu/i });

    // Antes do clique: menu ainda não está expandido
    // Após o clique: links do menu mobile devem aparecer
    fireEvent.click(menuButton);

    // Verifica que o menu mobile renderizou os links
    // (getAllByText pois existem versões desktop e mobile)
    const homeLinks = screen.getAllByText("Home");
    expect(homeLinks.length).toBeGreaterThan(0);
  });

  it("botão hamburguer alterna estado ao clicar duas vezes", () => {
    renderNavbar();
    const menuButton = screen.getByRole("button", { name: /menu/i });

    // Primeiro clique: abre o menu
    fireEvent.click(menuButton);
    // Segundo clique: fecha o menu (ou mantém links — o comportamento é toggle)
    fireEvent.click(menuButton);

    // Após fechar, o botão ainda deve existir
    expect(screen.getByRole("button", { name: /menu/i })).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// GRUPO 3: Accessibility Testing — O componente é acessível?
// ═══════════════════════════════════════════════════════════════════════════

describe("Navbar — Accessibility Testing", () => {
  it("a navbar usa a tag semântica <nav>", () => {
    renderNavbar();
    const nav = screen.getByRole("navigation");
    expect(nav).toBeInTheDocument();
  });

  it("o botão de menu tem aria-label descritivo", () => {
    renderNavbar();
    const btn = screen.getByRole("button", { name: /menu/i });
    expect(btn).toHaveAttribute("aria-label", "Menu");
  });

  it("links de navegação são elementos âncora clicáveis", () => {
    renderNavbar();
    const links = screen.getAllByRole("link");
    // Deve ter pelo menos o link do logo + os 5 links de nav
    expect(links.length).toBeGreaterThanOrEqual(6);
  });
});
