import {
  clearSession,
  getCurrentUser,
  hasStoredSession,
  login as loginRequest,
  logout as logoutRequest,
  type UserPublic,
} from "../api";

export type CurrentUser = UserPublic;

export const authApi = {
  hasSession: hasStoredSession,
  clear: clearSession,

  async login(identifier: string, password: string): Promise<CurrentUser> {
    await loginRequest(identifier, password);
    return getCurrentUser();
  },

  me: getCurrentUser,
  logout: logoutRequest,
};
