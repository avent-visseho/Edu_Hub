import type { LucideIcon } from 'lucide-react';
import {
  Award,
  BarChart3,
  BookOpen,
  Bus,
  Building2,
  ClipboardCheck,
  FileSearch,
  FileText,
  GraduationCap,
  Home,
  Landmark,
  Library,
  Lightbulb,
  Map,
  ScrollText,
  Search,
  Settings,
  ShieldCheck,
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
        libelle: 'Établissements',
        libelleSimple: 'Écoles',
        pictogramme: '🏫',
        href: '/etablissements',
        icone: Building2,
        permission: 'etablissements:READ',
      },
      {
        libelle: 'Classes',
        libelleSimple: 'Classes',
        pictogramme: '📚',
        href: '/classes',
        icone: BookOpen,
        permission: 'classes:READ',
      },
      {
        libelle: 'Bulletins',
        libelleSimple: 'Notes',
        pictogramme: '📝',
        href: '/bulletins',
        icone: FileText,
        permission: 'bulletins:READ',
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
        libelle: 'Résultats',
        libelleSimple: 'Résultats',
        pictogramme: '🏆',
        href: '/resultats',
        icone: Award,
        permission: 'resultats:READ',
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
    titre: 'Vie étudiante',
    entrees: [
      {
        libelle: 'Bourses et aides',
        libelleSimple: 'Bourses',
        pictogramme: '💶',
        href: '/bourses',
        icone: Landmark,
        permission: 'bourses:READ',
      },
      {
        libelle: 'Transport',
        libelleSimple: 'Bus',
        pictogramme: '🚌',
        href: '/transport',
        icone: Bus,
        permission: 'transport:READ',
      },
      {
        libelle: 'Bibliothèque',
        libelleSimple: 'Livres',
        pictogramme: '📖',
        href: '/bibliotheque',
        icone: Library,
        permission: 'bibliotheque:READ',
      },
      {
        libelle: 'Projets',
        libelleSimple: 'Projets',
        pictogramme: '💡',
        href: '/projets',
        icone: Lightbulb,
        permission: 'projets:READ',
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
        libelle: "Journal d'audit",
        libelleSimple: 'Journal',
        pictogramme: '📜',
        href: '/administration/audit',
        icone: FileSearch,
        permission: 'audit:READ',
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
