import client from './client';

export const authApi = {
  login: (email, password) =>
    client.post('/auth/login', { email, password }),

  demoLogin: () =>
    client.post('/auth/demo-login'),

  logout: () =>
    client.post('/auth/logout'),

  refresh: () =>
    client.post('/auth/refresh'),

  register: (data) =>
    client.post('/auth/register', data),

  getProfile: () =>
    client.get('/auth/me'),

  updateProfile: (data) =>
    client.put('/auth/profile', data),

  changePassword: (oldPassword, newPassword) =>
    client.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
};
