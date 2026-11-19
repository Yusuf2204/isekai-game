/** Localization and Translation Dictionaries (English & Indonesian).
 *
 * Implements bilingual support for Isekai: A Life Unwritten.
 */

export type Language = 'en' | 'id';

export interface TranslationDictionary {
  common: {
    title: string;
    subtitle: string;
    loading: string;
    error: string;
    return: string;
    cancel: string;
    confirm: string;
    gold: string;
    day: string;
    turn: string;
    generation: string;
    xp: string;
    level: string;
  };
  header: {
    systemStatus: string;
    devInfo: string;
    connectionFailed: string;
    checkBackend: string;
  };
  mainMenu: {
    tagline: string;
    beginNew: string;
    communing: string;
    continueSaved: string;
    noSaved: string;
    chronicles: string;
    connecting: string;
    realmConnection: string;
  };
  characterCreation: {
    title: string;
    reincarnationTitle: string;
    subtitle: string;
    legacyInherited: string;
    mortalName: string;
    namePlaceholder: string;
    gender: string;
    male: string;
    female: string;
    nonBinary: string;
    lineageRace: string;
    background: string;
    startingGold: string;
    startingSkills: string;
    reroll: string;
    returnToVoid: string;
    awaken: string;
    awakening: string;
    racialTrait: string;
  };
  gameplay: {
    tabs: {
      activities: string;
      world: string;
      profile: string;
      npcs: string;
      conditions: string;
    };
    health: string;
    stamina: string;
    fatigue: string;
    wait: string;
    activitiesTitle: string;
    explore: string;
    work: string;
    rest: string;
    shortRest: string;
    longRest: string;
    train: string;
    socialize: string;
    trade: string;
    dangerLevel: string;
    population: string;
    currentPresence: string;
    travelHere: string;
    travelDuration: string;
    attributesTitle: string;
    pointsAvailable: string;
    allocatePoint: string;
    skillsTitle: string;
    noSkills: string;
    inventoryTitle: string;
    emptyKnapsack: string;
    useItem: string;
    chronicleTitle: string;
    chronicleEmpty: string;
    endSession: string;
    concludeConfirm: string;
    eventEncounter: string;
  };
  npcs: {
    title: string;
    subtitle: string;
    talk: string;
    gift: string;
    affinity: string;
    trust: string;
    noNpcs: string;
    dialogueWith: string;
  };
  conditions: {
    healthy: string;
    severity: string;
    duration: string;
    remedies: string;
    applyTreatment: string;
    cost: string;
  };
  combat: {
    title: string;
    combatChronicle: string;
    attack: string;
    defend: string;
    useSkill: string;
    useItem: string;
    flee: string;
    victory: string;
    victorySubtitle: string;
    claimVictory: string;
    defeat: string;
    defeatSubtitle: string;
    crossThreshold: string;
    fled: string;
    fledSubtitle: string;
    returnExploration: string;
    noBattle: string;
    hp: string;
    defendingActive: string;
  };
  death: {
    title: string;
    crossed: string;
    mortalRecord: string;
    cause: string;
    daysSurvived: string;
    coinsAmassed: string;
    lineage: string;
    achievementsEarned: string;
    legacyPassed: string;
    reincarnate: string;
    concludeJourney: string;
  };
  summary: {
    title: string;
    subtitle: string;
    totalGens: string;
    totalDays: string;
    totalAch: string;
    status: string;
    active: string;
    concluded: string;
    lineage: string;
    living: string;
    fallen: string;
    retired: string;
    legacyPassedDesc: string;
    returnMenu: string;
    viewHistory: string;
  };
  history: {
    title: string;
    subtitle: string;
    returnMenu: string;
    noChronicles: string;
    beginFirst: string;
    sessionNumber: string;
    generationsCount: string;
    recordedDate: string;
    resume: string;
    inProgress: string;
    concluded: string;
  };
  races: Record<string, { name: string; trait: string; desc: string }>;
  backgrounds: Record<string, { name: string; desc: string }>;
  attributes: Record<string, string>;
  timesOfDay: Record<string, string>;
}

export const translations: Record<Language, TranslationDictionary> = {
  en: {
    common: {
      title: 'Isekai: A Life Unwritten',
      subtitle: 'Single-Player Dark Fantasy Text RPG',
      loading: 'Loading...',
      error: 'Notice',
      return: 'Back',
      cancel: 'Cancel',
      confirm: 'Confirm',
      gold: 'Gold',
      day: 'Day',
      turn: 'Turn',
      generation: 'Generation',
      xp: 'XP',
      level: 'Level',
    },
    header: {
      systemStatus: 'System Status & Architecture Details',
      devInfo: 'Development Info',
      connectionFailed: 'Connection Failed',
      checkBackend: 'Make sure the backend is running on http://localhost:8001',
    },
    mainMenu: {
      tagline: 'A single soul transmigrates through generations in the dark kingdom of Eldoria.',
      beginNew: 'Begin New Life',
      communing: 'Communing with the Void...',
      continueSaved: 'Continue Saved Life',
      noSaved: 'Continue (No Saved Game)',
      chronicles: 'Chronicles of Past Lives (Session History)',
      connecting: 'Connecting to Eldoria backend...',
      realmConnection: 'Realm Connection',
    },
    characterCreation: {
      title: 'Genesis of a New Life',
      reincarnationTitle: 'Transmigration of the Soul',
      subtitle: 'Choose the mortal vessel and origin for your soul in the kingdom of Eldoria.',
      legacyInherited: 'Ancestral Legacy Inherited',
      mortalName: 'Mortal Name',
      namePlaceholder: 'e.g. Rowan the Wanderer',
      gender: 'Gender Presentation',
      male: 'Male',
      female: 'Female',
      nonBinary: 'Non-Binary',
      lineageRace: 'Lineage & Race',
      background: 'Background & Social Origin',
      startingGold: 'Starting Gold',
      startingSkills: 'Starting Skills',
      reroll: '🎲 Reroll / Randomize',
      returnToVoid: '← Return to Void',
      awaken: 'Awaken in Eldoria',
      awakening: 'Awakening Vessel...',
      racialTrait: 'Racial Trait',
    },
    gameplay: {
      tabs: {
        activities: 'Activities',
        world: 'World & Travel',
        profile: 'Profile & Stats',
        npcs: 'NPCs & Figures',
        conditions: 'Conditions',
      },
      health: 'Health',
      stamina: 'Stamina',
      fatigue: 'Fatigue',
      wait: 'Wait 1 Period',
      activitiesTitle: 'Daily Deeds & Activities',
      explore: 'Explore Location',
      work: 'Work for Wages',
      rest: 'Rest & Recover',
      shortRest: 'Short Rest (1 Period)',
      longRest: 'Long Rest (Inn / 2 Periods)',
      train: 'Train Skills',
      socialize: 'Socialize in Tavern',
      trade: 'Trade in Market',
      dangerLevel: 'Danger',
      population: 'Population',
      currentPresence: '📍 Currently Present',
      travelHere: 'Travel Here',
      travelDuration: '1-2 Periods',
      attributesTitle: 'Attributes & Mastery',
      pointsAvailable: 'Point(s) Available to Allocate',
      allocatePoint: '+ Allocate',
      skillsTitle: 'Developed Skills',
      noSkills: 'No specialized skills developed yet. Perform work or explore to cultivate skills.',
      inventoryTitle: 'Inventory',
      emptyKnapsack: 'Empty knapsack.',
      useItem: 'Use Item',
      chronicleTitle: 'Chronicle of Deeds',
      chronicleEmpty: 'The chronicle pages await your deeds...',
      endSession: 'Conclude Epoch / End Session',
      concludeConfirm: 'Are you sure you want to conclude this life epoch? Any living character will be peacefully retired.',
      eventEncounter: 'Encounter',
    },
    npcs: {
      title: 'Notable Figures & Denizens',
      subtitle: 'Form bonds, glean rumors, or exchange gifts.',
      talk: '💬 Talk',
      gift: '🎁 Gift 10g',
      affinity: 'Affinity',
      trust: 'Trust',
      noNpcs: 'No notable figures present here at this hour.',
      dialogueWith: 'Dialogue with',
    },
    conditions: {
      healthy: '🌱 The body is whole and free of mortal afflictions.',
      severity: 'Severity',
      duration: 'Duration',
      remedies: 'Available Remedies',
      applyTreatment: 'Apply Treatment',
      cost: 'Cost',
    },
    combat: {
      title: 'Turn-Based Combat',
      combatChronicle: 'Combat Chronicle',
      attack: 'Attack (-10 STA)',
      defend: 'Defend (+5 STA, -50% DMG)',
      useSkill: 'Strike Skill (-15 STA)',
      useItem: 'Use Potion',
      flee: 'Flee Battle',
      victory: 'Victory Achieved!',
      victorySubtitle: 'The beast has fallen before your blade and resolve.',
      claimVictory: 'Claim Victory & Continue Journey',
      defeat: 'Defeated in Combat',
      defeatSubtitle: 'Your mortal vessel has succumbed to lethal wounds.',
      crossThreshold: 'Cross the Threshold of Death',
      fled: 'Tactical Retreat Successful',
      fledSubtitle: 'You broke away from the skirmish and found safety.',
      returnExploration: 'Return to Exploration',
      noBattle: 'No battle currently engaged.',
      hp: 'HP',
      defendingActive: '🛡️ Defending Stance Active',
    },
    death: {
      title: 'THE VESSEL PERISHES',
      crossed: 'has crossed the threshold of death.',
      mortalRecord: 'Mortal Record & Obituary',
      cause: 'Cause',
      daysSurvived: 'Days Survived',
      coinsAmassed: 'Coins Amassed',
      lineage: 'Lineage',
      achievementsEarned: 'Deeds & Achievements Earned',
      legacyPassed: 'Ancestral Legacy Left Behind',
      reincarnate: 'Reincarnate into Generation',
      concludeJourney: 'Conclude Session & View History',
    },
    summary: {
      title: 'CHRONICLES OF THE TRANSMIGRATED SOUL',
      subtitle: 'The complete generational tapestry woven by your soul in Eldoria.',
      totalGens: 'TOTAL GENERATIONS',
      totalDays: 'TOTAL DAYS LIVED',
      totalAch: 'ACHIEVEMENTS EARNED',
      status: 'SESSION STATUS',
      active: 'ACTIVE',
      concluded: 'CONCLUDED',
      lineage: 'Generational Lineage',
      living: 'Living',
      fallen: 'Fallen',
      retired: 'Retired',
      legacyPassedDesc: 'Legacy passed to descendants:',
      returnMenu: 'Return to Main Menu',
      viewHistory: 'Begin a Brand New Journey',
    },
    history: {
      title: 'Archived Chronicles',
      subtitle: 'Past epochs and soul journeys recorded across Eldoria.',
      returnMenu: '← Return to Menu',
      noChronicles: 'No past chronicles found. A fresh destiny awaits your first soul.',
      beginFirst: 'Begin First Journey',
      sessionNumber: 'Session',
      generationsCount: 'Generation(s)',
      recordedDate: 'Recorded',
      resume: 'Resume Active Session',
      inProgress: 'In Progress',
      concluded: 'Concluded',
    },
    races: {
      human: {
        name: 'Human',
        trait: 'Adaptable Spirit',
        desc: 'The most numerous and versatile race in Eldoria, capable of forging any destiny.',
      },
      elf: {
        name: 'Elf',
        trait: 'Arcane Attunement',
        desc: 'Graceful custodians of ancient magic, deeply attuned to mana and wisdom.',
      },
      beastkin: {
        name: 'Beastkin',
        trait: 'Keen Senses',
        desc: 'Swift hunters with beast-like ears and instincts, swift and vigilant.',
      },
      dwarf: {
        name: 'Dwarf',
        trait: 'Iron Constitution',
        desc: 'Stout craftsmen with bodies resistant to poison and tireless resolve.',
      },
      dragonkin: {
        name: 'Dragonkin',
        trait: 'Draconic Heritage',
        desc: 'Descendants of ancient drakes with scale-hardened resilience and fierce power.',
      },
      demonkin: {
        name: 'Demonkin',
        trait: 'Fiendish Legacy',
        desc: 'Carriers of dark planar blood, walking the edge of immense magic and suspicion.',
      },
    },
    backgrounds: {
      commoner: {
        name: 'Commoner',
        desc: 'Born to hard work and humility, possessing resilient survival skills.',
      },
      merchant_family: {
        name: 'Merchant Family',
        desc: 'Raised among coin-scales and ledger books, skilled in trade and negotiation.',
      },
      orphan: {
        name: 'Orphan',
        desc: 'Raised by the streets, relying purely on sharp wits and survival instinct.',
      },
      noble_descendant: {
        name: 'Noble Descendant',
        desc: 'Born to privilege and intrigue, educated in court diplomacy and arcane arts.',
      },
      former_slave: {
        name: 'Former Slave',
        desc: 'Tempered by suffering and iron will, hardened to endure the harshest trials.',
      },
    },
    attributes: {
      strength: 'Strength (STR)',
      agility: 'Agility (AGI)',
      intelligence: 'Intelligence (INT)',
      vitality: 'Vitality (VIT)',
      luck: 'Luck (LUK)',
    },
    timesOfDay: {
      morning: 'Morning',
      afternoon: 'Afternoon',
      evening: 'Evening',
      night: 'Night',
    },
  },
  id: {
    common: {
      title: 'Isekai: A Life Unwritten',
      subtitle: 'RPG Teks Dark Fantasy Pemain Tunggal',
      loading: 'Memuat...',
      error: 'Pemberitahuan',
      return: 'Kembali',
      cancel: 'Batal',
      confirm: 'Konfirmasi',
      gold: 'Emas',
      day: 'Hari',
      turn: 'Giliran',
      generation: 'Generasi',
      xp: 'EXP',
      level: 'Level',
    },
    header: {
      systemStatus: 'Status Sistem & Detail Arsitektur',
      devInfo: 'Informasi Pengembangan',
      connectionFailed: 'Koneksi Terputus',
      checkBackend: 'Pastikan server backend berjalan pada http://localhost:8001',
    },
    mainMenu: {
      tagline: 'Satu jiwa bereinkarnasi lintas generasi di kerajaan kelam Eldoria.',
      beginNew: 'Mulai Kehidupan Baru',
      communing: 'Menghubungkan dengan Kehampaan...',
      continueSaved: 'Lanjutkan Kehidupan Tersimpan',
      noSaved: 'Lanjutkan (Tidak Ada Simpanan)',
      chronicles: 'Babad Kehidupan Lalu (Riwayat Sesi)',
      connecting: 'Menghubungkan ke server Eldoria...',
      realmConnection: 'Koneksi Alam',
    },
    characterCreation: {
      title: 'Penciptaan Kehidupan Baru',
      reincarnationTitle: 'Transmigrasi Jiwa',
      subtitle: 'Pilih wadah fana dan asal-usul jiwamu di kerajaan Eldoria.',
      legacyInherited: 'Warisan Leluhur Diterima',
      mortalName: 'Nama Fana',
      namePlaceholder: 'mis. Rowan Sang Pengelana',
      gender: 'Representasi Gender',
      male: 'Pria',
      female: 'Wanita',
      nonBinary: 'Non-Biner',
      lineageRace: 'Silsilah & Ras',
      background: 'Latar Belakang & Asal Sosial',
      startingGold: 'Koin Emas Awal',
      startingSkills: 'Keahlian Awal',
      reroll: '🎲 Acak / Reroll',
      returnToVoid: '← Kembali ke Kehampaan',
      awaken: 'Bangkit di Eldoria',
      awakening: 'Membangkitkan Wadah...',
      racialTrait: 'Ciri Khas Ras',
    },
    gameplay: {
      tabs: {
        activities: 'Aktivitas Harian',
        world: 'Dunia & Perjalanan',
        profile: 'Profil & Atribut',
        npcs: 'Tokoh & Penduduk',
        conditions: 'Kondisi Fisik',
      },
      health: 'Kesehatan (HP)',
      stamina: 'Stamina',
      fatigue: 'Kelelahan',
      wait: 'Tunggu 1 Periode',
      activitiesTitle: 'Tindakan & Pekerjaan Harian',
      explore: 'Jelajahi Lokasi',
      work: 'Bekerja Mencari Upah',
      rest: 'Istirahat & Pulihkan Diri',
      shortRest: 'Istirahat Singkat (1 Periode)',
      longRest: 'Istirahat Panjang (Penginapan / 2 Periode)',
      train: 'Latih Keahlian',
      socialize: 'Bersosialisasi di Kedai',
      trade: 'Berdagang di Pasar',
      dangerLevel: 'Tingkat Bahaya',
      population: 'Populasi',
      currentPresence: '📍 Sedang Berada di Sini',
      travelHere: 'Bepergian ke Sini',
      travelDuration: '1-2 Periode',
      attributesTitle: 'Atribut & Kemampuan Diri',
      pointsAvailable: 'Poin Tersedia untuk Dialokasikan',
      allocatePoint: '+ Tambah',
      skillsTitle: 'Keahlian Terlatih',
      noSkills: 'Belum ada keahlian khusus. Bekerja atau jelajahi alam untuk mengasah keahlian.',
      inventoryTitle: 'Inventaris & Tas',
      emptyKnapsack: 'Tas ransel masih kosong.',
      useItem: 'Gunakan Barang',
      chronicleTitle: 'Babad Catatan Perjalanan',
      chronicleEmpty: 'Lembaran babad menanti perbuatan besarmu...',
      endSession: 'Akhiri Zaman / Sesi Kehidupan',
      concludeConfirm: 'Yakin ingin mengakhiri zaman kehidupan ini? Karakter yang masih hidup akan pensiun dengan damai.',
      eventEncounter: 'Peristiwa',
    },
    npcs: {
      title: 'Tokoh Penting & Penduduk',
      subtitle: 'Jalin hubungan, dengar kabar burung, atau berikan hadiah.',
      talk: '💬 Bicara',
      gift: '🎁 Beri Hadiah 10g',
      affinity: 'Keakraban',
      trust: 'Kepercayaan',
      noNpcs: 'Tidak ada tokoh penting di tempat ini pada jam ini.',
      dialogueWith: 'Percakapan dengan',
    },
    conditions: {
      healthy: '🌱 Tubuh sehat walafiat tanpa penyakit atau gangguan fana.',
      severity: 'Keparahan',
      duration: 'Sisa Waktu',
      remedies: 'Obat & Penanganan yang Tersedia',
      applyTreatment: 'Lakukan Pengobatan',
      cost: 'Biaya',
    },
    combat: {
      title: 'Pertarungan Turn-Based',
      combatChronicle: 'Riwayat Pertarungan',
      attack: '⚔️ Serang',
      defend: '🛡️ Bertahan (Kurangi 50% Kerusakan)',
      useSkill: '⚡ Gunakan Skill',
      useItem: '🧪 Gunakan Barang',
      flee: '🏃 Kabur dari Pertempuran',
      victory: 'Kemenangan Diraih!',
      victorySubtitle: 'Musuh telah tumbang di hadapan tekad dan senjatamu.',
      claimVictory: 'Ambil Hadiah & Lanjutkan Perjalanan',
      defeat: 'Gugur dalam Pertarungan',
      defeatSubtitle: 'Wadah fanamu telah menyerah akibat luka fatal yang diderita.',
      crossThreshold: 'Lintasi Ambang Kematian',
      fled: 'Berhasil Melarikan Diri',
      fledSubtitle: 'Kamu berhasil melepaskan diri dan mencari perlindungan aman.',
      returnExploration: 'Kembali Menjelajah',
      noBattle: 'Tidak ada pertempuran yang sedang berlangsung.',
      hp: 'HP',
      defendingActive: '🛡️ Posisi Bertahan Aktif',
    },
    death: {
      title: 'WADAH FANA TELAH GUGUR',
      crossed: 'telah melintasi gerbang kematian.',
      mortalRecord: 'Catatan Jiwa & Obituari',
      cause: 'Penyebab Kematian',
      daysSurvived: 'Hari Bertahan Hidup',
      coinsAmassed: 'Koin yang Dikumpulkan',
      lineage: 'Garis Silsilah',
      achievementsEarned: 'Pencapaian & Jasa yang Diraih',
      legacyPassed: 'Pusaka Warisan untuk Keturunan',
      reincarnate: 'Reinkarnasi ke Generasi',
      concludeJourney: 'Akhiri Sesi & Buka Riwayat Sejarah',
    },
    summary: {
      title: 'Babad Silsilah Generasi',
      subtitle: 'Rekam jejak transmigrasi jiwa melintasi zaman di kerajaan Eldoria.',
      totalGens: 'Total Generasi',
      totalDays: 'Total Hari Hidup',
      totalAch: 'Pencapaian',
      status: 'Status Sesi',
      active: 'Sedang Berlangsung',
      concluded: 'Selesai / Ditutup',
      lineage: 'Silsilah Keturunan',
      living: 'Masih Hidup',
      fallen: 'Gugur',
      retired: 'Pensiun Damai',
      legacyPassedDesc: 'Warisan diteruskan ke generasi penerus',
      returnMenu: '← Kembali ke Menu Utama',
      viewHistory: 'Buka Arsip Babad →',
    },
    history: {
      title: 'Arsip Babad Kerajaan',
      subtitle: 'Catatan zaman masa lalu dan perjalanan jiwa di tanah Eldoria.',
      returnMenu: '← Kembali ke Menu Utama',
      noChronicles: 'Belum ada catatan babad. Takdir baru menanti jiwa pertamamu.',
      beginFirst: 'Mulai Perjalanan Pertama',
      sessionNumber: 'Sesi',
      generationsCount: 'Generasi',
      recordedDate: 'Tercatat',
      resume: 'Lanjutkan Sesi Aktif',
      inProgress: 'Sedang Berjalan',
      concluded: 'Selesai',
    },
    races: {
      human: {
        name: 'Manusia',
        trait: 'Semangat Adaptif',
        desc: 'Ras paling banyak dan serbaguna di Eldoria, mampu mengukir takdir apa pun.',
      },
      elf: {
        name: 'Peri (Elf)',
        trait: 'Penyelarasan Gaib',
        desc: 'Penjaga anggun sihir kuno, memiliki ikatan mendalam dengan mana dan kebijaksanaan.',
      },
      beastkin: {
        name: 'Manusia Hewan (Beastkin)',
        trait: 'Indra Tajam',
        desc: 'Pemburu gesit dengan telinga dan naluri satwa liar, sigap dan selalu waspada.',
      },
      dwarf: {
        name: 'Kurcaci (Dwarf)',
        trait: 'Ketahanan Besi',
        desc: 'Penempa tangguh dengan tubuh kebal racun dan tekad yang pantang menyerah.',
      },
      dragonkin: {
        name: 'Manusia Naga (Dragonkin)',
        trait: 'Warisan Naga',
        desc: 'Keturunan naga purba dengan sisik pelindung dan kekuatan fisik yang menggentarkan.',
      },
      demonkin: {
        name: 'Manusia Iblis (Demonkin)',
        trait: 'Pusaka Fiend',
        desc: 'Pembawa darah entitas alam bawah, memadukan sihir luar biasa dengan tatapan curiga dunia.',
      },
    },
    backgrounds: {
      commoner: {
        name: 'Rakyat Jelata',
        desc: 'Terbiasa dengan kerja keras dan kesederhanaan, memiliki keahlian bertahan hidup yang tangguh.',
      },
      merchant_family: {
        name: 'Keluarga Pedagang',
        desc: 'Tumbuh di antara timbangan koin dan buku kas, piawai dalam berdagang dan bernegosiasi.',
      },
      orphan: {
        name: 'Anak Yatim Piatu',
        desc: 'Dibesarkan kerasnya jalanan, bertumpu murni pada kecerdikan dan naluri bertahan hidup.',
      },
      noble_descendant: {
        name: 'Keturunan Bangsawan',
        desc: 'Terlahir dalam privilese dan intrik istana, terdidik dalam diplomasi dan seni sihir.',
      },
      former_slave: {
        name: 'Mantan Budak',
        desc: 'Ditempa oleh penderitaan dan tekad membaja, tabah menghadapi cobaan hidup terberat sekalipun.',
      },
    },
    attributes: {
      strength: 'Kekuatan (STR)',
      agility: 'Kelincahan (AGI)',
      intelligence: 'Kecerdasan (INT)',
      vitality: 'Ketahanan (VIT)',
      luck: 'Keberuntungan (LUK)',
    },
    timesOfDay: {
      morning: 'Pagi Hari',
      afternoon: 'Siang Hari',
      evening: 'Sore Hari',
      night: 'Malam Hari',
    },
  },
};
