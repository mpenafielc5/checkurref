/**
 * Lo que solo se ve con la barra lateral desplegada (textos del menú, nombre y
 * rol del usuario). Aparece con la misma espera que el ancho de la barra (ver
 * AppSidebar) y se oculta en cuanto el mouse sale. Solo se vuelve transparente:
 * sigue en la página, así que los lectores de pantalla lo leen siempre.
 */
export const REVEAL_ON_EXPAND =
  "whitespace-nowrap opacity-0 transition-opacity duration-(--cr-duration-fast) group-hover/sidebar:opacity-100 group-hover/sidebar:delay-(--cr-sidebar-expand-delay) group-has-[:focus-visible]/sidebar:opacity-100";
