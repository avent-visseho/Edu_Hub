/**
 * Client HTTP de l'API EduHub.
 *
 * Il gère les jetons, le rafraîchissement automatique de la session et la
 * traduction des erreurs de l'API en messages exploitables par l'interface.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

const CLE_ACCES = 'eduhub.jeton.acces';
const CLE_RAFRAICHISSEMENT = 'eduhub.jeton.rafraichissement';

export interface ErreurApiCharge {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export class ErreurApi extends Error {
  readonly statut: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(statut: number, charge: ErreurApiCharge) {
    super(charge.message);
    this.name = 'ErreurApi';
    this.statut = statut;
    this.code = charge.code;
    this.details = charge.details ?? {};
  }

  /** Vrai lorsque l'utilisateur doit se reconnecter. */
  get estAuthentification(): boolean {
    return this.statut === 401;
  }

  /** Vrai lorsque l'action est refusée faute de droits. */
  get estPermission(): boolean {
    return this.statut === 403;
  }
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ------------------------------------------------------------------
//  Jetons
// ------------------------------------------------------------------

export const jetons = {
  acces(): string | null {
    if (typeof window === 'undefined') return null;
    try {
      return window.localStorage.getItem(CLE_ACCES);
    } catch {
      return null;
    }
  },
  rafraichissement(): string | null {
    if (typeof window === 'undefined') return null;
    try {
      return window.localStorage.getItem(CLE_RAFRAICHISSEMENT);
    } catch {
      return null;
    }
  },
  enregistrer(acces: string, rafraichissement: string): void {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(CLE_ACCES, acces);
      window.localStorage.setItem(CLE_RAFRAICHISSEMENT, rafraichissement);
    } catch {
      /* Navigation privée : la session reste valable le temps de l'onglet. */
    }
  },
  effacer(): void {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.removeItem(CLE_ACCES);
      window.localStorage.removeItem(CLE_RAFRAICHISSEMENT);
    } catch {
      /* Rien à faire. */
    }
  },
};

// ------------------------------------------------------------------
//  Requêtes
// ------------------------------------------------------------------

interface OptionsRequete extends Omit<RequestInit, 'body'> {
  /** Corps JSON, sérialisé automatiquement. */
  corps?: unknown;
  /** Paramètres de requête, les valeurs nulles étant ignorées. */
  parametres?: Record<string, string | number | boolean | null | undefined>;
  /** N'ajoute pas le jeton d'accès — pour les routes publiques. */
  publique?: boolean;
  /** Renvoie la réponse brute plutôt que du JSON — pour les PDF et les CSV. */
  brut?: boolean;
}

function construireUrl(
  chemin: string,
  parametres?: OptionsRequete['parametres'],
): string {
  const url = new URL(`${BASE}${chemin.startsWith('/') ? chemin : `/${chemin}`}`);
  if (parametres) {
    for (const [cle, valeur] of Object.entries(parametres)) {
      if (valeur !== null && valeur !== undefined && valeur !== '') {
        url.searchParams.set(cle, String(valeur));
      }
    }
  }
  return url.toString();
}

async function lireErreur(reponse: Response): Promise<ErreurApiCharge> {
  try {
    const charge = await reponse.json();
    if (charge?.error) return charge.error as ErreurApiCharge;
    if (typeof charge?.detail === 'string') {
      return { code: 'erreur', message: charge.detail };
    }
    if (Array.isArray(charge?.detail)) {
      // Erreurs de validation FastAPI : on les rend lisibles.
      const messages = charge.detail
        .map((entree: { loc?: unknown[]; msg?: string }) => {
          const champ = Array.isArray(entree.loc) ? entree.loc.slice(1).join('.') : '';
          return champ ? `${champ} : ${entree.msg}` : entree.msg;
        })
        .filter(Boolean);
      return { code: 'donnees_invalides', message: messages.join(' — ') };
    }
  } catch {
    /* Réponse non JSON. */
  }
  return {
    code: 'erreur_reseau',
    message: `La requête a échoué (code ${reponse.status}).`,
  };
}

let rafraichissementEnCours: Promise<boolean> | null = null;

async function rafraichirSession(): Promise<boolean> {
  const jeton = jetons.rafraichissement();
  if (!jeton) return false;

  // Un seul rafraîchissement simultané, quelles que soient les requêtes en vol.
  rafraichissementEnCours ??= (async () => {
    try {
      const reponse = await fetch(construireUrl('/auth/rafraichir'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: jeton }),
      });
      if (!reponse.ok) return false;
      const charge = await reponse.json();
      jetons.enregistrer(charge.access_token, charge.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      rafraichissementEnCours = null;
    }
  })();

  return rafraichissementEnCours;
}

async function executer(chemin: string, options: OptionsRequete = {}): Promise<Response> {
  // « brut » est interprété par l'appelant : on l'écarte des options transmises à fetch.
  const { corps, parametres, publique, brut, headers, ...reste } = options;
  void brut;

  const entetes = new Headers(headers);
  if (corps !== undefined && !(corps instanceof FormData)) {
    entetes.set('Content-Type', 'application/json');
  }
  if (!publique) {
    const jeton = jetons.acces();
    if (jeton) entetes.set('Authorization', `Bearer ${jeton}`);
  }

  return fetch(construireUrl(chemin, parametres), {
    ...reste,
    headers: entetes,
    body:
      corps === undefined
        ? undefined
        : corps instanceof FormData
          ? corps
          : JSON.stringify(corps),
  });
}

/** Exécute une requête et renvoie la charge JSON typée. */
export async function requete<T>(chemin: string, options: OptionsRequete = {}): Promise<T> {
  let reponse = await executer(chemin, options);

  if (reponse.status === 401 && !options.publique) {
    const rafraichi = await rafraichirSession();
    if (rafraichi) {
      reponse = await executer(chemin, options);
    } else {
      jetons.effacer();
    }
  }

  if (!reponse.ok) {
    throw new ErreurApi(reponse.status, await lireErreur(reponse));
  }

  if (reponse.status === 204) return undefined as T;
  if (options.brut) return reponse as unknown as T;

  const type = reponse.headers.get('content-type') ?? '';
  if (!type.includes('application/json')) {
    return (await reponse.blob()) as unknown as T;
  }
  return (await reponse.json()) as T;
}

export const api = {
  get: <T>(chemin: string, parametres?: OptionsRequete['parametres'], options?: OptionsRequete) =>
    requete<T>(chemin, { ...options, method: 'GET', parametres }),

  post: <T>(chemin: string, corps?: unknown, options?: OptionsRequete) =>
    requete<T>(chemin, { ...options, method: 'POST', corps }),

  patch: <T>(chemin: string, corps?: unknown, options?: OptionsRequete) =>
    requete<T>(chemin, { ...options, method: 'PATCH', corps }),

  delete: <T>(chemin: string, options?: OptionsRequete) =>
    requete<T>(chemin, { ...options, method: 'DELETE' }),

  /**
   * Télécharge un fichier produit par l'API (PDF, CSV) et déclenche
   * l'enregistrement. Certains exports décrivent ce qu'il faut produire dans un
   * corps de requête : `corps` bascule alors l'appel en POST.
   */
  async telecharger(
    chemin: string,
    nomFichier: string,
    parametres?: OptionsRequete['parametres'],
    corps?: unknown,
  ): Promise<void> {
    const reponse = await executer(chemin, {
      method: corps === undefined ? 'GET' : 'POST',
      parametres,
      corps,
    });
    if (!reponse.ok) throw new ErreurApi(reponse.status, await lireErreur(reponse));

    const blob = await reponse.blob();
    const url = URL.createObjectURL(blob);
    const lien = document.createElement('a');
    lien.href = url;
    lien.download = nomFichier;
    document.body.appendChild(lien);
    lien.click();
    lien.remove();
    URL.revokeObjectURL(url);
  },

  /** Ouvre un document dans un nouvel onglet, en conservant l'authentification. */
  async ouvrir(chemin: string, parametres?: OptionsRequete['parametres']): Promise<void> {
    const reponse = await executer(chemin, { method: 'GET', parametres });
    if (!reponse.ok) throw new ErreurApi(reponse.status, await lireErreur(reponse));
    const url = URL.createObjectURL(await reponse.blob());
    window.open(url, '_blank', 'noopener');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  },
};
