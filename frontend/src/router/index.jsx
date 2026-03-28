import { createBrowserRouter } from "react-router-dom";
import AuthLayout from "../layouts/AuthLayout";
import MainLayout from "../layouts/MainLayout";
import Home from "../pages/Home";
import Login from "../pages/Login";
import Cadastro from "../pages/Cadastro";
import AssistenteVirtual from "../pages/AssistenteVirtual";
import Jogos from "../pages/Jogos";
import Planos from "../pages/Planos";
import Pagamentos from "../pages/Pagamentos";
import Perfil from "../pages/Perfil";

export const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [
      { path: "/login", element: <Login /> },
      { path: "/cadastro", element: <Cadastro /> }
    ]
  },
  {
    element: <MainLayout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/assistente", element: <AssistenteVirtual /> },
      { path: "/jogos", element: <Jogos /> },
      { path: "/planos", element: <Planos /> },
      { path: "/pagamentos", element: <Pagamentos /> },
      { path: "/perfil", element: <Perfil /> }
    ]
  }
]);
