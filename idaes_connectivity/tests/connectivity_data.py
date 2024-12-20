import pytest

@pytest.fixture
def uky_csv():
    return [
        "Arcs,leach_mixer::ScalarMixer,leach::ScalarLeachingTrain,leach_liquid_feed::ScalarFeed,sl_sep1::ScalarSLSeparator,leach_solid_feed::ScalarFeed,precipitator::ScalarPrecipitator,sl_sep2::ScalarSLSeparator,leach_sx_mixer::ScalarMixer,leach_filter_cake_liquid::ScalarProduct,leach_filter_cake::ScalarProduct,precip_sep::ScalarSeparator,precip_purge::ScalarProduct,precip_sx_mixer::ScalarMixer,roaster::ScalarREEOxalateRoaster,solex_cleaner_load::ScalarSolventExtraction,solex_cleaner_strip::ScalarSolventExtraction,cleaner_mixer::ScalarMixer,cleaner_org_make_up::ScalarFeed,acid_feed3::ScalarFeed,cleaner_sep::ScalarSeparator,cleaner_purge::ScalarProduct,solex_rougher_load::ScalarSolventExtraction,load_sep::ScalarSeparator,solex_rougher_scrub::ScalarSolventExtraction,rougher_mixer::ScalarMixer,rougher_org_make_up::ScalarFeed,acid_feed1::ScalarFeed,scrub_sep::ScalarSeparator,solex_rougher_strip::ScalarSolventExtraction,acid_feed2::ScalarFeed,rougher_sep::ScalarSeparator,sc_circuit_purge::ScalarProduct",
        "leaching_feed_mixture,-1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "leaching_liq_feed,1,0,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "leaching_liquid_outlet,0,-1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "leaching_sol_feed,0,1,0,0,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "leaching_solid_outlet,0,-1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "precip_aq_outlet,0,0,0,0,0,-1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "precip_solid_outlet,0,0,0,0,0,-1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sl_sep1_liquid_outlet,0,0,0,-1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sl_sep1_retained_liquid_outlet,0,0,0,-1,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sl_sep1_solid_outlet,0,0,0,-1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sl_sep2_aq_purge,0,0,0,0,0,0,0,0,0,0,-1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sl_sep2_aq_recycle,0,0,0,0,0,0,0,0,0,0,-1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sl_sep2_liquid_outlet,0,0,0,0,0,0,-1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sl_sep2_retained_liquid_outlet,0,0,0,0,0,0,-1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sl_sep2_solid_outlet,0,0,0,0,0,0,-1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sx_cleaner_load_aq_feed,0,0,0,0,0,0,0,0,0,0,0,0,-1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sx_cleaner_load_aq_outlet,0,0,0,0,0,0,0,1,0,0,0,0,0,0,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sx_cleaner_load_org_outlet,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sx_cleaner_mixed_org_recycle,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sx_cleaner_org_feed,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sx_cleaner_strip_acid_feed,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sx_cleaner_strip_aq_outlet,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "sx_cleaner_strip_org_outlet,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0",
        "sx_cleaner_strip_org_purge,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,1,0,0,0,0,0,0,0,0,0,0,0",
        "sx_cleaner_strip_org_recycle,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,0,0,0,0,0,0,0",
        "sx_rougher_load_aq_feed,0,0,0,0,0,0,0,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0",
        "sx_rougher_load_aq_outlet,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,1,0,0,0,0,0,0,0,0,0",
        "sx_rougher_load_aq_recycle,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,0,0,0,0,0,0,0,0,0",
        "sx_rougher_load_org_outlet,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,0,1,0,0,0,0,0,0,0,0",
        "sx_rougher_mixed_org_recycle,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,0,0",
        "sx_rougher_org_feed,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,-1,0,0,0,0,0,0",
        "sx_rougher_scrub_acid_feed,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,-1,0,0,0,0,0",
        "sx_rougher_scrub_aq_outlet,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,0,0,0,1,0,0,0,0",
        "sx_rougher_scrub_aq_recycle,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,0,0,0,0",
        "sx_rougher_scrub_org_outlet,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,0,0,0,0,1,0,0,0",
        "sx_rougher_strip_acid_feed,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,-1,0,0",
        "sx_rougher_strip_aq_outlet,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,0,0,0",
        "sx_rougher_strip_org_outlet,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,0,1,0",
        "sx_rougher_strip_org_purge,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,1",
        "sx_rougher_strip_org_recycle,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,-1,0",
    ]


@pytest.fixture
def uky_mermaid():
    return [
        "flowchart LR",
        "   Unit_B[leach_mixer::ScalarMixer]",
        "   Unit_C[leach::ScalarLeachingTrain]",
        "   Unit_D[leach_liquid_feed::ScalarFeed]",
        "   Unit_E[sl_sep1::ScalarSLSeparator]",
        "   Unit_F[leach_solid_feed::ScalarFeed]",
        "   Unit_G[precipitator::ScalarPrecipitator]",
        "   Unit_H[sl_sep2::ScalarSLSeparator]",
        "   Unit_I[leach_sx_mixer::ScalarMixer]",
        "   Unit_J[leach_filter_cake_liquid::ScalarProduct]",
        "   Unit_K[leach_filter_cake::ScalarProduct]",
        "   Unit_L[precip_sep::ScalarSeparator]",
        "   Unit_M[precip_purge::ScalarProduct]",
        "   Unit_N[precip_sx_mixer::ScalarMixer]",
        "   Unit_O[roaster::ScalarREEOxalateRoaster]",
        "   Unit_P[solex_cleaner_load::ScalarSolventExtraction]",
        "   Unit_Q[solex_cleaner_strip::ScalarSolventExtraction]",
        "   Unit_R[cleaner_mixer::ScalarMixer]",
        "   Unit_S[cleaner_org_make_up::ScalarFeed]",
        "   Unit_T[acid_feed3::ScalarFeed]",
        "   Unit_U[cleaner_sep::ScalarSeparator]",
        "   Unit_V[cleaner_purge::ScalarProduct]",
        "   Unit_W[solex_rougher_load::ScalarSolventExtraction]",
        "   Unit_X[load_sep::ScalarSeparator]",
        "   Unit_Y[solex_rougher_scrub::ScalarSolventExtraction]",
        "   Unit_Z[rougher_mixer::ScalarMixer]",
        "   Unit_AA[rougher_org_make_up::ScalarFeed]",
        "   Unit_AB[acid_feed1::ScalarFeed]",
        "   Unit_AC[scrub_sep::ScalarSeparator]",
        "   Unit_AD[solex_rougher_strip::ScalarSolventExtraction]",
        "   Unit_AE[acid_feed2::ScalarFeed]",
        "   Unit_AF[rougher_sep::ScalarSeparator]",
        "   Unit_AG[sc_circuit_purge::ScalarProduct]",
        "   Unit_B --> Unit_C",
        "   Unit_D --> Unit_B",
        "   Unit_C --> Unit_E",
        "   Unit_F --> Unit_C",
        "   Unit_C --> Unit_E",
        "   Unit_G --> Unit_H",
        "   Unit_G --> Unit_H",
        "   Unit_E --> Unit_I",
        "   Unit_E --> Unit_J",
        "   Unit_E --> Unit_K",
        "   Unit_L --> Unit_M",
        "   Unit_L --> Unit_N",
        "   Unit_H --> Unit_L",
        "   Unit_H --> Unit_O",
        "   Unit_H --> Unit_O",
        "   Unit_N --> Unit_P",
        "   Unit_P --> Unit_I",
        "   Unit_P --> Unit_Q",
        "   Unit_R --> Unit_P",
        "   Unit_S --> Unit_R",
        "   Unit_T --> Unit_Q",
        "   Unit_Q --> Unit_G",
        "   Unit_Q --> Unit_U",
        "   Unit_U --> Unit_V",
        "   Unit_U --> Unit_R",
        "   Unit_I --> Unit_W",
        "   Unit_W --> Unit_X",
        "   Unit_X --> Unit_B",
        "   Unit_W --> Unit_Y",
        "   Unit_Z --> Unit_W",
        "   Unit_AA --> Unit_Z",
        "   Unit_AB --> Unit_Y",
        "   Unit_Y --> Unit_AC",
        "   Unit_AC --> Unit_B",
        "   Unit_Y --> Unit_AD",
        "   Unit_AE --> Unit_AD",
        "   Unit_AD --> Unit_N",
        "   Unit_AD --> Unit_AF",
        "   Unit_AF --> Unit_AG",
        "   Unit_AF --> Unit_Z",
        "",
    ]
