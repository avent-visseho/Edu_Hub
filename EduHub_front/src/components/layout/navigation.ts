import type { LucideIcon } from 'lucide-react';
import {
  Award,
  BarChart3,
  BedDouble,
  BookOpen,
  BookUser,
  Briefcase,
  Bus,
  Building2,
  Building,
  ClipboardCheck,
  ClipboardList,
  ClipboardPen,
  Compass,
  FileSearch,
  FileText,
  FlaskConical,
  GraduationCap,
  HeartPulse,
  Home,
  Landmark,
  Layers,
  Network,
  Languages,
  Library,
  Lightbulb,
  Map,
  MessageSquare,
  Gavel,
  MapPin,
  Scale,
  PenLine,
  MonitorPlay,
  ScrollText,
  Search,
  Settings,
  ShieldCheck,
  UtensilsCrossed,
  Users,
  UserSquare2,
} from 'lucide-react';

export interface EntreeNavigation {
  libelle: string;
  /** Libellé court utilisé par l'interface simplifiée. */
  libelleSimple: string;
  pictogramme: string;
  href: string;
  icone: LucideIcon;
  /** Permission requise, au format `ressource:action`. */
  permission?: string;
  /**
   * Libellé employé pour les comptes dont la portée est personnelle.
   *
   * « Apprenants » décrit un registre national ; pour l'élève qui n'y trouve
   * que sa propre fiche, « Mon dossier » dit la vérité de ce qu'il ouvre. Les
   * clés sont des codes de rôle, avec « PERSONNEL » comme valeur de repli.
   */
  libellePersonnel?: Record<string, string>;
}

/**
 * Libellé d'une entrée pour un compte donné.
 *
 * Les comptes à portée personnelle ne voient que leurs propres données :
 * « Apprenants » décrit un registre national là où l'élève n'ouvrira que sa
 * fiche. La barre latérale et l'accueil personnel s'appuient tous deux sur
 * cette fonction, afin de ne pas diverger.
 */
export function libelleEntree(
  entree: EntreeNavigation,
  niveauScope: string,
  roles: string[],
): string {
  if (niveauScope !== 'PERSONNEL' || !entree.libellePersonnel) return entree.libelle;
  const parRole = roles.map((role) => entree.libellePersonnel?.[role]).find(Boolean);
  return parRole ?? entree.libellePersonnel.PERSONNEL ?? entree.libelle;
}

export interface GroupeNavigation {
  titre: string;
  entrees: EntreeNavigation[];
}

/**
 * Arborescence de navigation.
 *
 * Chaque entrée porte sa permission : la barre latérale ne montre que ce que
 * l'utilisateur peut réellement ouvrir.
 */
export const NAVIGATION: GroupeNavigation[] = [
  {
    titre: 'Pilotage',
    entrees: [
      {
        libelle: 'Tableau de bord',
        libelleSimple: 'Accueil',
        pictogramme: '🏠',
        href: '/tableau-de-bord',
        icone: Home,
      },
      {
        libelle: 'Statistiques nationales',
        libelleSimple: 'Chiffres',
        pictogramme: '📊',
        href: '/statistiques',
        icone: BarChart3,
        permission: 'analytics:READ',
      },
      {
        libelle: 'Cartographie',
        libelleSimple: 'Carte',
        pictogramme: '🗺️',
        href: '/cartographie',
        icone: Map,
        permission: 'etablissements:READ',
      },
      {
        libelle: 'Recherche avancée',
        libelleSimple: 'Chercher',
        pictogramme: '🔎',
        href: '/recherche',
        icone: Search,
        permission: 'recherche_avancee:READ',
      },
    ],
  },
  {
    titre: 'Scolarité',
    entrees: [
      {
        libelle: 'Apprenants',
        libelleSimple: 'Élèves',
        pictogramme: '🧑‍🎓',
        href: '/apprenants',
        libellePersonnel: { PERSONNEL: 'Mon dossier', PARENT: 'Mes enfants' },
        icone: Users,
        permission: 'apprenants:READ',
      },
      {
        libelle: 'Enseignants',
        libelleSimple: 'Profs',
        pictogramme: '👩‍🏫',
        href: '/enseignants',
        icone: UserSquare2,
        permission: 'enseignants:READ',
      },
      {
        libelle: 'Annuaire',
        libelleSimple: 'Contacts',
        pictogramme: '📇',
        href: '/annuaire',
        icone: BookUser,
        permission: 'parents:READ',
      },
      {
        libelle: 'Établissements',
        libelleSimple: 'Écoles',
        pictogramme: '🏫',
        href: '/etablissements',
        icone: Building2,
        permission: 'etablissements:READ',
      },
      {
        libelle: 'Infrastructures',
        libelleSimple: 'Bâtiments',
        pictogramme: '🏢',
        href: '/infrastructures',
        icone: Building,
        permission: 'infrastructures:READ',
      },
      {
        libelle: 'Classes',
        libelleSimple: 'Classes',
        pictogramme: '📚',
        href: '/classes',
        libellePersonnel: { PERSONNEL: 'Ma classe' },
        icone: BookOpen,
        permission: 'classes:READ',
      },
      {
        libelle: 'Inscriptions',
        libelleSimple: 'Inscrire',
        pictogramme: '📋',
        href: '/inscriptions',
        libellePersonnel: { PERSONNEL: 'Mon inscription' },
        icone: ClipboardPen,
        permission: 'inscriptions:READ',
      },
      {
        libelle: 'Évaluations',
        libelleSimple: 'Devoirs',
        pictogramme: '✏️',
        href: '/evaluations',
        icone: ClipboardList,
        permission: 'evaluations:READ',
      },
      {
        libelle: 'Bulletins',
        libelleSimple: 'Notes',
        pictogramme: '📝',
        href: '/bulletins',
        libellePersonnel: { PERSONNEL: 'Mes bulletins', PARENT: 'Bulletins de mes enfants' },
        icone: FileText,
        permission: 'bulletins:READ',
      },
      {
        libelle: 'Cours en ligne',
        libelleSimple: 'Cours',
        pictogramme: '💻',
        href: '/apprentissage',
        icone: MonitorPlay,
        permission: 'apprentissage:READ',
      },
      {
        libelle: 'Alphabétisation',
        libelleSimple: 'Lire et écrire',
        pictogramme: '🔤',
        href: '/alphabetisation',
        icone: Languages,
        permission: 'apprentissage:READ',
      },
    ],
  },
  {
    titre: 'Examens et concours',
    entrees: [
      {
        libelle: 'Sessions',
        libelleSimple: 'Examens',
        pictogramme: '🎓',
        href: '/examens',
        icone: GraduationCap,
        permission: 'sessions:READ',
      },
      {
        libelle: 'Candidats',
        libelleSimple: 'Candidats',
        pictogramme: '🧾',
        href: '/candidats',
        icone: ClipboardCheck,
        permission: 'candidats:READ',
      },
      {
        libelle: 'Centres de composition',
        libelleSimple: 'Centres',
        pictogramme: '📍',
        href: '/centres',
        icone: MapPin,
        permission: 'centres:READ',
      },
      {
        libelle: 'Correction des copies',
        libelleSimple: 'Corriger',
        pictogramme: '🖊️',
        href: '/correction',
        icone: PenLine,
        permission: 'copies:READ',
      },
      {
        libelle: 'Jurys et surveillance',
        libelleSimple: 'Jurys',
        pictogramme: '⚖️',
        href: '/jurys',
        icone: Scale,
        permission: 'jurys:READ',
      },
      {
        libelle: 'Résultats',
        libelleSimple: 'Résultats',
        pictogramme: '🏆',
        href: '/resultats',
        libellePersonnel: { PERSONNEL: 'Mes résultats' },
        icone: Award,
        permission: 'resultats:READ',
      },
      {
        libelle: 'Contentieux',
        libelleSimple: 'Recours',
        pictogramme: '⚖️',
        href: '/contentieux',
        icone: Gavel,
        permission: 'contentieux:READ',
      },
      {
        libelle: "Banque d'épreuves",
        libelleSimple: 'Sujets',
        pictogramme: '🗂️',
        href: '/banque-epreuves',
        icone: ScrollText,
        permission: 'archives:READ',
      },
    ],
  },
  {
    titre: 'Orientation et insertion',
    entrees: [
      {
        libelle: 'Orientation',
        libelleSimple: 'Après le bac',
        pictogramme: '🧭',
        href: '/orientation',
        libellePersonnel: { PERSONNEL: 'Mon orientation' },
        icone: Compass,
        permission: 'orientation:READ',
      },
      {
        libelle: 'Projets',
        libelleSimple: 'Projets',
        pictogramme: '💡',
        href: '/projets',
        libellePersonnel: { PERSONNEL: 'Mes projets' },
        icone: Lightbulb,
        permission: 'projets:READ',
      },
      {
        libelle: 'Stages et emploi',
        libelleSimple: 'Travail',
        pictogramme: '💼',
        href: '/emploi',
        libellePersonnel: { PERSONNEL: 'Mes candidatures' },
        icone: Briefcase,
        permission: 'emploi:READ',
      },
      {
        libelle: 'Recherche scientifique',
        libelleSimple: 'Science',
        pictogramme: '🔬',
        href: '/recherche-scientifique',
        icone: FlaskConical,
        permission: 'recherche:READ',
      },
    ],
  },
  {
    titre: 'Vie étudiante',
    entrees: [
      {
        libelle: 'Bourses et aides',
        libelleSimple: 'Bourses',
        pictogramme: '💶',
        href: '/bourses',
        libellePersonnel: { PERSONNEL: 'Mes bourses' },
        icone: Landmark,
        permission: 'bourses:READ',
      },
      {
        libelle: 'Transport',
        libelleSimple: 'Bus',
        pictogramme: '🚌',
        href: '/transport',
        libellePersonnel: { PERSONNEL: 'Mon transport' },
        icone: Bus,
        permission: 'transport:READ',
      },
      {
        libelle: 'Logement',
        libelleSimple: 'Chambres',
        pictogramme: '🛏️',
        href: '/logement',
        libellePersonnel: { PERSONNEL: 'Mon logement' },
        icone: BedDouble,
        permission: 'logement:READ',
      },
      {
        libelle: 'Restauration',
        libelleSimple: 'Repas',
        pictogramme: '🍽️',
        href: '/restauration',
        icone: UtensilsCrossed,
        permission: 'restauration:READ',
      },
      {
        libelle: 'Santé scolaire',
        libelleSimple: 'Santé',
        pictogramme: '🩺',
        href: '/sante',
        icone: HeartPulse,
        permission: 'sante:READ',
      },
      {
        libelle: 'Bibliothèque',
        libelleSimple: 'Livres',
        pictogramme: '📖',
        href: '/bibliotheque',
        libellePersonnel: { PERSONNEL: 'Mes emprunts' },
        icone: Library,
        permission: 'bibliotheque:READ',
      },
      {
        libelle: 'Messagerie',
        libelleSimple: 'Messages',
        pictogramme: '✉️',
        href: '/messagerie',
        icone: MessageSquare,
      },
    ],
  },
  {
    titre: 'Administration',
    entrees: [
      {
        libelle: 'Comptes et rôles',
        libelleSimple: 'Comptes',
        pictogramme: '🔐',
        href: '/administration/comptes',
        icone: ShieldCheck,
        permission: 'utilisateurs:READ',
      },
      {
        libelle: 'Gouvernance',
        libelleSimple: 'Organisation',
        pictogramme: '🏛️',
        href: '/gouvernance',
        icone: Network,
        permission: 'structures:READ',
      },
      {
        libelle: "Journal d'audit",
        libelleSimple: 'Journal',
        pictogramme: '📜',
        href: '/administration/audit',
        icone: FileSearch,
        permission: 'audit:READ',
      },
      {
        libelle: 'Référentiels',
        libelleSimple: 'Listes',
        pictogramme: '🗂️',
        href: '/administration/referentiels',
        icone: Layers,
        permission: 'referentiels:READ',
      },
      {
        libelle: 'Paramètres',
        libelleSimple: 'Réglages',
        pictogramme: '⚙️',
        href: '/administration/parametres',
        icone: Settings,
        permission: 'parametres:READ',
      },
    ],
  },
];
