import { createSimpleRestDataProvider } from "@refinedev/rest/simple-rest";
import { API_URL, TOKEN_KEY } from "./constants";

export const { dataProvider, kyInstance } = createSimpleRestDataProvider({
  apiURL: API_URL,
  kyOptions: {
    hooks: {
      beforeRequest: [
        (request) => {
          const token = localStorage.getItem(TOKEN_KEY);
          if (token) {
            request.headers.set("Authorization", `Bearer ${token}`);
          }
        },
      ],
    },
  },
});
