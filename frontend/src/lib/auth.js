import { supabase } from './supabase';
import { DEMO_USER_ID } from './constants';

export const getAuthUser = async () => {
  if (localStorage.getItem('demoSession')) {
    return {
      data: {
        user: {
          id: DEMO_USER_ID,
          email: 'demo@hackathon.com',
        },
      },
      error: null,
    };
  }

  return await supabase.auth.getUser();
};

export const getDemoSession = () => {
  if (!localStorage.getItem('demoSession')) return null;
  return {
    user: { id: DEMO_USER_ID, email: 'demo@hackathon.com' },
  };
};
