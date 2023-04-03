#!/usr/bin/env python
# coding: utf-8

# `TTbarResCoffeaOutputs` Notebook to produce Coffea output files for an all hadronic $t\bar{t}$ analysis.  The outputs will be found in the corresponding **CoffeaOutputs** directory.

import os, psutil
import time
import copy
import itertools
import scipy.stats as ss
import awkward as ak
import numpy as np
import glob as glob
import pandas as pd
import argparse as ap
import re
from coffea import processor, nanoevents, util
from coffea.nanoevents.methods import candidate
from coffea.nanoevents import NanoAODSchema, BaseSchema
from numpy.random import RandomState
import mplhep as hep
import matplotlib.colors as colors
# from hist.intervals import ratio_uncertainty

ak.behavior.update(candidate.behavior)
# -- Note: Use process.memory_info()[0] for python 2.7. Else, use process.memory_info()
process = psutil.Process(os.getpid()) # Keep track of memory usage
maindirectory = os.getcwd()
os.chdir('../') # Runs the code from within the working directory without manually changing all directory paths!

def mkdir_p(mypath):
    '''Creates a directory. equivalent to using mkdir -p on the command line'''

    from errno import EEXIST

    try:
        os.makedirs(mypath)
    except OSError as exc: # Python >2.5
        if exc.errno == EEXIST and os.path.isdir(mypath):
            pass
        else: raise
        
def plotratio2d(numerator, denominator, ax=None, cmap='Blues', cbar=True):
    NumeratorAxes = numerator.axes
    DenominatorAxes = denominator.axes
    
    # integer number of bins in this axis #
    NumeratorAxis1_BinNumber = NumeratorAxes[0].size - 3 # Subtract 3 to remove overflow
    NumeratorAxis2_BinNumber = NumeratorAxes[1].size - 3
    
    DenominatorAxis1_BinNumber = DenominatorAxes[0].size - 3 
    DenominatorAxis2_BinNumber = DenominatorAxes[1].size - 3 
    
    if(NumeratorAxis1_BinNumber != DenominatorAxis1_BinNumber 
       or NumeratorAxis2_BinNumber != DenominatorAxis2_BinNumber):
        raise Exception('Numerator and Denominator axes are different sizes; Cannot perform division.')
    # else:
    #     Numerator = numerator.to_hist()
    #     Denominator = denominator.to_hist()
        
    ratio = numerator / denominator.values()

    return hep.hist2dplot(ratio, ax=ax, cmap=cmap, norm=colors.Normalize(0.,1.), cbar=cbar)

def FlavEffList(Flavor, Output, Dataset, bdiscDirectory, Save):
    """
    Flavor          ---> string: either 'b', 'c', or 'udsg'
    Output          ---> Coffea Object: Output that is returned from running processor
    Dataset         ---> string: the dataset string (ex QCD, RSGluon1000, etc...) corresponding to Output
    bdiscDirectory  ---> string; Directory path for chosen b discriminator
    Save            ---> bool; Save mistag rates or not
    """
    SaveDirectory = maindirectory + '/FlavorTagEfficiencies/' + bdiscDirectory + Flavor + 'tagEfficiencyTables/'
    mkdir_p(SaveDirectory)
    for subjet in ['s01', 's02', 's11', 's12']:

        eff_numerator = Output[Flavor + '_eff_numerator_' + subjet + '_manualbins'][{'dataset': Dataset}]
        eff_denominator = Output[Flavor + '_eff_denominator_' + subjet + '_manualbins'][{'dataset': Dataset}]

        eff = plotratio2d(eff_numerator, eff_denominator) #ColormeshArtists object
        
        eff_data = eff[0].get_array().data # This is what goes into pandas dataframe
        eff_data = np.nan_to_num(eff_data, nan=0.0) # If eff bin is empty, call it zero

        # ---- Define pt and eta bins from the numerator or denominator hist objects ---- #
        pt_bins = []
        eta_bins = []

        for iden in eff_numerator.axes['subjetpt']:
            pt_bins.append(iden)
        for iden in eff_numerator.axes['subjeteta']:
            eta_bins.append(iden)

        # ---- Define the Efficiency List as a Pandas Dataframe ---- #
        pd.set_option("display.max_rows", None, "display.max_columns", None)
        EfficiencyList = pd.DataFrame(
                            eff_data,
                            pd.MultiIndex.from_product( [pt_bins, eta_bins], names=['pt', 'eta'] ),
                            ['efficiency']
                        )

        print('\n\t--------------------- Subjet ' + subjet + ' ' + Flavor + ' Efficiency ---------------------\n')
        print('====================================================================\n')
        print(EfficiencyList)
        
        # ---- Save the Efficiency List as .csv ---- #
        if Save:
            filename = dataset + '_' + subjet + '_' + Flavor + 'tageff.csv'
            EfficiencyList.to_csv(SaveDirectory+filename)
            print('\nSaved ' + filename)

            
            
def main():
    #    -----------------------------------------------
    #    PPPPPP     A    RRRRRR    SSSSS EEEEEEE RRRRRR      
    #    P     P   A A   R     R  S      E       R     R     
    #    P     P  A   A  R     R S       E       R     R     
    #    PPPPPP   AAAAA  RRRRRR   SSSSS  EEEEEEE RRRRRR      
    #    P       A     A R   R         S E       R   R       
    #    P       A     A R    R       S  E       R    R      
    #    P       A     A R     R SSSSS   EEEEEEE R     R 
    #    -----------------------------------------------

    # class STEP1(ap.Action):
    #     def __call__(self, parser, namespace, values, option_string):
    #         print("\nStep 1: Create Mistag Rates for Chosen Year\n")
    #         setattr(namespace, 'APV', 'no')
    #         setattr(namespace, 'runmistag', True)
    #         setattr(namespace, 'medium', True)
    #         setattr(namespace, 'saveMistag', True)
    #         setattr(namespace, 'chunksize', 20000)

    # Parser = ap.ArgumentParser(prog='TTbarResCoffeaOutputs.py', description='something')
    Parser = ap.ArgumentParser(prog='Run.py', formatter_class=ap.RawDescriptionHelpFormatter, description='''\
    -----------------------------------------------------------------------------
    Run the TTbarAllHadProcessor script.  
    All objects for each dataset ran can be saved as its own .coffea output file.
    -----------------------------------------------------------------------------''', 
                                    epilog='''\
                                    Available List of Dataset Strings:
                                    Key:
                                    -------------------------------------------------------------------------------
                                    <x> = integer from [1, 5]
                                    <y> = integer either 0 or 5 
                                    <x> = <y> = 5 is not an available string to be included in dataset string names
                                    -------------------------------------------------------------------------------
                                    QCD
                                    DM<x><y>00, DM
                                    RSGluon<x><y>00, RSGluon
                                    TTbar
                                    JetHT
                                    SingleMu\n
                                        **NOTE**
                                        =========================
                                        JetHT 2016 letters: B - H
                                        JetHT 2017 letters: B - F
                                        JetHT 2018 letters: A - D
                                        =========================\n

                                        =============================================================================
                                        JetHT 2016 triggers: HLT_PFHT900 (default), HLT_PFHT800, HLT_AK8PFJet450, HLT_AK8PFJet360_TrimMass30
                                        JetHT 2017 triggers:
                                        JetHT 2018 triggers:
                                        =============================================================================\n

        Example of a usual workflow on Coffea-Casa to make the relevant coffea outputs:\n
        0.) Make Outputs for Flavor and Trigger Efficiencies
    ./Run.py -C -med -F QCD TTbar DM RSGluon -a no -y 2016 --dask --saveFlav
    ./Run.py -C -med -T -a no -y 2016 --dask --saveTrig\n
        1.) Create Mistag Rates that will be used to estimate NTMJ background
    ./Run.py -C -y 2016 --step 1
    python Run.py -C -med -m -a no -y 2016 --saveMistag\n
        2.) Make Outputs for the first Uproot Job with no weights applied (outside of MC weights that come with the nanoAOD)
    ./Run.py -C -y 2016 --step 2
    python Run.py -C -med -d QCD TTbar JetHT DM RSGluon -a no -y 2016 --uproot 1 --save\n
        3.) Make Outputs for the second Uproot Job with only mistag rate applied to JetHT and TTbar
    ./Run.py -C -y 2016 --step 3
    python Run.py -C -med -A QCD TTbar JetHT DM RSGluon -a no -y 2016 --save\n
        4.) Make Outputs for the second Uproot Job with only mistag rate applied to JetHT and TTbar, and mass modification of JetHT and TTbar in pre-tag region
    ./Run.py -C -y 2016 --step 4
    python Run.py -C -med -M QCD TTbar JetHT DM RSGluon -a no -y 2016 --save\n
        5.) Make Outputs for the second Uproot Job with systematics, on top of mistag rate application and mass modification
    ./Run.py -C -y 2016 --step 5
    python Run.py -C -med -d QCD TTbar JetHT DM RSGluon -a no -y 2016 --uproot 2 --bTagSyst central --useEff --save\n
      ''')
    # ---- Necessary arguments ---- #
    StartGroup = Parser.add_mutually_exclusive_group()
    StartGroup.add_argument('-t', '--runtesting', action='store_true', help='Only run a select few root files defined in the code.')
    StartGroup.add_argument('-m', '--runmistag', action='store_true',help='Make data mistag rate where ttbar contamination is removed (as well as ttbar mistag rate)')
    StartGroup.add_argument('-T', '--runtrigeff', action='store_true', help='Create trigger efficiency hist coffea output objects for chosen condition') 
    StartGroup.add_argument('-F', '--runflavoreff', type=str, nargs='+', help='Create flavor efficiency hist coffea output objects for chosen MC datasets')
    StartGroup.add_argument('-M', '--runMMO', type=str, nargs='+', help='Run Mistag-weight and Mass modification Only (no other systematics for uproot 2)')
    StartGroup.add_argument('-A', '--runAMO', type=str, nargs='+', help='Run (Apply) Mistag-weight Only (no other systematics for uproot 2)')
    StartGroup.add_argument('-d', '--rundataset', type=str, nargs='+', help='List of datasets to be ran/loaded')

    RedirectorGroup = Parser.add_mutually_exclusive_group(required=True)
    RedirectorGroup.add_argument('-C', '--casa', action='store_true', help='Use Coffea-Casa redirector: root://xcache/')
    RedirectorGroup.add_argument('-L', '--lpc', action='store_true', help='Use CMSLPC redirector: root://cmsxrootd.fnal.gov/')
    RedirectorGroup.add_argument('-W', '--winterfell', action='store_true', help='Get available files from UB Winterfell /mnt/data/cms')

    BDiscriminatorGroup = Parser.add_mutually_exclusive_group()
    BDiscriminatorGroup.add_argument('-l', '--loose', action='store_true', help='Apply loose bTag discriminant cut')
    BDiscriminatorGroup.add_argument('-med', '--medium', action='store_true', help='Apply medium bTag discriminant cut')
    BDiscriminatorGroup.add_argument('-med2016', '--medium2016', action='store_true', help='Apply medium bTag discriminant cut from 2016 AN')
    
    Parser.add_argument('--mistagcorrect', action='store_true', help='Remove ttbar contamination when making mistag rates')
    Parser.add_argument('-a', '--APV', type=str, choices=['yes', 'no'], help='Do datasets have APV?', default='no')
    Parser.add_argument('-trigs', '--triggers', type=str, nargs='+', help='Triggers to Apply')
    Parser.add_argument('-y', '--year', type=int, choices=[2016, 2017, 2018, 0], help='Year(s) of data/MC of the datasets you want to run uproot with.  Choose 0 for all years simultaneously (0 option not yet finished; TBA).', default=2016)

    # ---- Other arguments ---- #
    Parser.add_argument('--uproot', type=int, choices=[1, 2], help='1st run or 2nd run of uproot job.  If not specified, both the 1st and 2nd job will be run one after the other.')
    Parser.add_argument('--letters', type=str, nargs='+', help='Choose letter(s) of jetHT to run over')
    Parser.add_argument('--chunks', type=int, help='Number of chunks of data to run for given dataset(s)')
    Parser.add_argument('--chunksize', type=int, help='Size of each chunk to run for given dataset(s)')
    Parser.add_argument('--save', action='store_true', help='Choose to save the uproot job as a coffea output for later analysis')
    Parser.add_argument('--saveMistag', action='store_true', help='Save mistag rate calculated from running either --uproot 1 or --mistag')
    Parser.add_argument('--saveTrig', action='store_true', help='Save uproot job with trigger analysis outputs (Only if -T selected)')
    Parser.add_argument('--saveFlav', action='store_true', help='Save uproot job with flavor efficiency outputs (Only if -F selected)')
    Parser.add_argument('--dask', action='store_true', help='Try the dask executor (experimental) for some fast processing!')
    Parser.add_argument('--newCluster', action='store_true', help='Use Manually Defined Cluster (Must Disable Default Cluster First if Running in CoffeaCasa)')
    Parser.add_argument('--timeout', type=float, help='How many seconds should dask wait for scheduler to connect')
    Parser.add_argument('--useEff', action='store_true', help='Use MC bTag efficiencies for bTagging systematics')
    Parser.add_argument('--tpt', action='store_true', help='Apply top pT re-weighting for uproot 2')

    Parser.add_argument('--step', type=int, choices=[1, 2, 3, 4, 5], help='Easily run a certain step of the workflow')

    UncertaintyGroup = Parser.add_mutually_exclusive_group()
    UncertaintyGroup.add_argument('--bTagSyst', type=str, choices=['central', 'up', 'down'], help='Choose Unc.')
    UncertaintyGroup.add_argument('--tTagSyst', type=str, choices=['central', 'up', 'down'], help='Choose Unc.')
    UncertaintyGroup.add_argument('--ttXSSyst', type=str, choices=['central', 'up', 'down'], help='ttbar cross section systematics.  Choose Unc.')
    UncertaintyGroup.add_argument('--lumSyst', type=str, choices=['central', 'up', 'down'], help='Luminosity systematics.  Choose Unc.')
    UncertaintyGroup.add_argument('--jes', type=str, choices=['central', 'up', 'down'], help='apply jes systematic weights. Choose Unc.')

    
    
    # systematic weights applied in the same processor
    Parser.add_argument('--pileup', action='store_true', help='apply pileup systematic weights')
    Parser.add_argument('--prefiring', action='store_true', help='apply prefiring systematic weights')
    Parser.add_argument('--pdf', action='store_true', help='apply pdf systematic weights')
    Parser.add_argument('--hem', action='store_true', help='apply HEM cleaning')


    args = Parser.parse_args()
    
    Trigs_to_run = []
    defaultTriggers = []
    if args.year == 2016:
        defaultTriggers.append("HLT_PFHT900")
    print(f'\nDefault Triggers: {defaultTriggers}\n')
    Trigs_to_run = defaultTriggers
    if args.triggers:
        for itrig in args.triggers:
            if itrig not in defaultTriggers:
                Trigs_to_run.append(itrig)    
    print(f'All Triggers Chosen: {Trigs_to_run}\n\n')

    if args.step == 1:
        print('\n\nStep 1: Get and Save Mistag Rates\n')
        # args.medium = True
        args.runmistag = True
        args.saveMistag = True
        # args.chunksize = 20000
    elif args.step == 2: 
        print('\n\nStep 2: Run and Save the First Uproot Job\n')
        # args.medium = True
        args.rundataset = ['QCD', 'TTbar', 'JetHT', 'DM', 'RSGluon']
        args.save = True
        # args.chunksize = 20000
        args.uproot = 1
    elif args.step == 3: 
        print('\n\nStep 3: Run and Save the Second Uproot Job with Only Mistag Rate Application\n')
        # args.medium = True
        args.runAMO = ['QCD', 'TTbar', 'JetHT', 'DM', 'RSGluon']
        args.save = True
        # args.chunksize = 20000
    elif args.step == 4: 
        print('\n\nStep 4: Run and Save the Second Uproot Job with Only Mistag Rate and ModMass Applications\n')
        # args.medium = True
        args.runMMO = ['QCD', 'TTbar', 'JetHT', 'DM', 'RSGluon']
        args.save = True
        # args.chunksize = 20000
    elif args.step == 5: 
        print('\n\nStep 5: Run and Save the Second Uproot Job\n')
        # args.medium = True
        args.rundataset = ['QCD', 'TTbar', 'JetHT', 'DM', 'RSGluon']
        args.save = True
        # args.chunksize = 20000
        args.uproot = 2
    else:
        print('Manual Job Being Performed Below:')

    StartGroupList = np.array([args.runtesting, args.runmistag, args.runtrigeff, args.runflavoreff, args.runMMO, args.runAMO, args.rundataset], dtype=object)
    BDiscriminatorGroupList = np.array([args.loose, args.medium, args.medium2016], dtype=object)

    if not np.any(StartGroupList): #if user forgets to assign something here or does not pick a specific step
        print('\n\nDefault run; No available dataset selected')
        args.rundataset = ['QCD']
        args.uproot = 1
        # args.medium = True
    if not np.any(BDiscriminatorGroupList): #if user forgets to assign something here or does not pick a specific step
        print('\n\nDefault Btag -> med;')
        args.medium = True

    TimeOut = 30.
    if args.timeout:
        TimeOut = args.timeout
    if args.runmistag and args.uproot:
        Parser.error('When running the --runmistag option do not specify --uproot.')
        quit()
    isTrigEffArg = args.runtrigeff
    if isTrigEffArg and args.uproot:
        Parser.error('When running --runtrigeff option do not specify --uproot.')
        quit()
    if isTrigEffArg == False and args.saveTrig:
        Parser.error('When not running some --runtrigeff option do not specify --saveTrig.')
        quit()
    if (args.runMMO or args.runAMO) and args.uproot:
        Parser.error('When running --runMMO or --runAMO option do not specify --uproot.')
        quit()

    #    -------------------------------------------------------
    #      OOO   PPPPPP  TTTTTTT IIIIIII   OOO   N     N   SSSSS     
    #     O   O  P     P    T       I     O   O  NN    N  S          
    #    O     O P     P    T       I    O     O N N   N S           
    #    O     O PPPPPP     T       I    O     O N  N  N  SSSSS      
    #    O     O P          T       I    O     O N   N N       S     
    #     O   O  P          T       I     O   O  N    NN      S      
    #      OOO   P          T    IIIIIII   OOO   N     N SSSSS   
    #    -------------------------------------------------------

    Redirector = None
    daskDirectory = ''
    envirDirectory = ''
    if args.casa:
        Redirector = 'root://xcache/'
        envirDirectory = 'dask-worker-space/'
    elif args.lpc:
        Redirector = 'root://cmsxrootd.fnal.gov/'
    elif args.winterfell:
        Redirector = '/mnt/data/cms'
    else:
        print('Redirector not selected properly; code should have terminated earlier!  Terminating now!')
        quit()
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    VFP = ''
    if args.APV == 'yes':
        VFP = 'preVFP'
    else:
        VFP = 'postVFP'
    convertLabel = {
        'preVFP': 'APV',
        'postVFP': 'noAPV'
    }
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    BDisc = 0.
    OldDisc = '' #Label the datasets that use the old discriminator cut from 2016 AN
    BDiscDirectory = ''
    if args.loose:
        BDisc = 0.1918
        BDiscDirectory = 'LooseBTag/'
    elif args.medium:
        BDisc = 0.5847
        BDiscDirectory = 'MediumBTag/'
    else:
        BDisc = 0.8484
        OldDisc = '_oldANdisc'
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    Testing = args.runtesting
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    LoadingUnweightedFiles = False 
    OnlyCreateLookupTables = False 
    if (args.uproot == 1 or args.runmistag) or (isTrigEffArg or args.runflavoreff):
        OnlyCreateLookupTables = True # stop the code after LUTs are displayed on the terminal; after 1st uproot job
    elif (args.uproot == 2 or args.runMMO or args.runAMO):
        LoadingUnweightedFiles = True # Load the 1st uproot job's coffea outputs if you only want to run the 2nd uproot job.
    else: # Default for running both 1st and 2nd uproot job
        LoadingUnweightedFiles = False 
        OnlyCreateLookupTables = False 
    #    ---------------------------------------------------------------------------------------------------------------------    #    

    RunAllRootFiles = False 
    if not args.chunks:
        RunAllRootFiles = True
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    UsingDaskExecutor = args.dask
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    SaveFirstRun = False
    SaveSecondRun = False
    if args.save:
        SaveFirstRun = True # Make a coffea output file of the first uproot job (without the systematics and corrections)
        SaveSecondRun = True # Make a coffea output file of the second uproot job (with the systematics and corrections)
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    method=''
    if not args.useEff and args.bTagSyst:
        method='_method2' # Use bTagging systematic method without MC efficiencies and label output accordingly
    #    ---------------------------------------------------------------------------------------------------------------------    #  

    # ============================================== #
    # ============================================== #
    # ==== Uncertainy/Systematic Configurations ==== #
    # ============================================== #
    # ============================================== #

    SystType = "" 
    UncType = ""
    SFfile = ""
    ApplybSF = False
    ApplytSF = False
    ApplyJES = False
    ApplyPDF = False
    ApplyPrefiring = False
    ApplyPUweights = False
    xsSystwgt = 1.
    lumSystwgt = 1.
    var="nominal" # nominal, up, or down for jet corrections

    # isData = False
    # MCDatasetChoices = ['QCD', 'TTbar', 'RSGluon', 'DM']
    # if 'JetHT' in args.rundataset:
    #     isData = True

    if UsingDaskExecutor:
        daskDirectory = envirDirectory
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    TPT = ''
    if args.tpt:
        TPT = '_TopReweight'

    if args.bTagSyst:
        UncType = "_btagUnc_"
        SystType = args.bTagSyst # string for btag SF evaluator --> "central", "up", or "down"
        ApplybSF = True
        SFfile = daskDirectory+'TTbarAllHadUproot/CorrectionFiles/SFs/bquark/subjet_btagging.json.gz'
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    elif args.ttXSSyst:
        UncType = "_ttXSUnc_"
        SystType = args.ttXSSyst # string for btag SF evaluator --> "central", "up", or "down"
        if args.ttXSSyst == 'up':
            xsSystwgt = 0.08
        elif args.ttXSSyst == 'down':
            xsSystwgt = -0.08
        else:
            pass
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    elif args.lumSyst:
        UncType = "_lumUnc_"
        SystType = args.lumSyst # string for btag SF evaluator --> "central", "up", or "down"
        if args.lumSyst == 'up':
            lumSystwgt = 0.025
        elif args.lumSyst == 'down':
            lumSystwgt = -0.025
        else:
            pass
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    elif args.tTagSyst:
        UncType = "_ttagUnc_"
        SystType = args.tTagSyst # string for ttag SF correction --> "central", "up", or "down"
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    elif args.jes:
        UncType = "_jesUnc_"
        SystType = args.jes        
        ApplyJES = True
        var = "nominal"
        if (args.jes == "up"): var = "up"
        if (args.jes == "down"): var = "down"
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    elif args.pdf:
        UncType = "_pdfUnc_"
        # SystType = 'pdf'
        ApplyPDF = True
    #    ---------------------------------------------------------------------------------------------------------------------    # 

    elif args.pileup:
        UncType = "_pileupUnc_"
        # SystType = ""
        ApplyPUweights = True
    #    ---------------------------------------------------------------------------------------------------------------------    # 
    
    elif args.prefiring:
        UncType = "_prefiringUnc_"
        # SystType = ''
        ApplyPrefiring = True
    #    ---------------------------------------------------------------------------------------------------------------------    # 
    
        
    elif args.prefiring:
        UncType = "_hemCleaning_"
        # SystType = ''
        ApplyPrefiring = True
    #    ---------------------------------------------------------------------------------------------------------------------    # 


    UncArgs = np.array([args.bTagSyst, args.tTagSyst, args.jes, args.ttXSSyst, args.lumSyst, args.pdf, args.pileup, args.prefiring])
    SystOpts = np.any(UncArgs) # Check to see if any uncertainty argument is used
    if (not OnlyCreateLookupTables) and (not SystOpts and (not args.runMMO and not args.runAMO)) :
        Parser.error('Only run second uproot job with a Systematic application (like --bTagSyst, --jes, etc.)')
        quit()
    #    -------------------------------------------------------    # 
    Chunk = [args.chunksize, args.chunks] # [chunksize, maxchunks]
    #    -------------------------------------------------------    # 

    from TTbarResProcessor import TTbarResProcessor, TriggerAnalysisProcessor, MCFlavorEfficiencyProcessor

    #    -------------------------------------------------------------------------------------------------------------------
    #    IIIIIII M     M PPPPPP    OOO   RRRRRR  TTTTTTT     DDDD       A    TTTTTTT    A      SSSSS EEEEEEE TTTTTTT   SSSSS     
    #       I    MM   MM P     P  O   O  R     R    T        D   D     A A      T      A A    S      E          T     S          
    #       I    M M M M P     P O     O R     R    T        D    D   A   A     T     A   A  S       E          T    S           
    #       I    M  M  M PPPPPP  O     O RRRRRR     T        D     D  AAAAA     T     AAAAA   SSSSS  EEEEEEE    T     SSSSS      
    #       I    M     M P       O     O R   R      T        D    D  A     A    T    A     A       S E          T          S     
    #       I    M     M P        O   O  R    R     T        D   D   A     A    T    A     A      S  E          T         S      
    #    IIIIIII M     M P         OOO   R     R    T        DDDD    A     A    T    A     A SSSSS   EEEEEEE    T    SSSSS  
    #    -------------------------------------------------------------------------------------------------------------------

    Letters = ['']
    if args.letters:
        Letters = args.letters

    namingConvention = 'UL' # prefix to help name every coffea output according to the selected options
    fileConvention = '/TTbarRes_0l_' # direct the saved coffea output to the appropriate directory ex.) postVFP/TTbarRes_0l_blahblah
    if args.year > 0:
        namingConvention = 'UL'+str(args.year-2000)+VFP # prefix to help name every coffea output according to the selected options
        fileConvention = str(args.year) + '/' + convertLabel[VFP] + '/TTbarRes_0l_' # direct the saved coffea output to the appropriate directory
    SaveLocation={ # Fill this dictionary with each type of dataset; use this dictionary when saving uproot jobs below
        namingConvention+'_TTbar': 'TT/' + BDiscDirectory + fileConvention,
        namingConvention+'_QCD': 'QCD/' + BDiscDirectory + fileConvention,
        namingConvention+'_DM': 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention,
        namingConvention+'_RSGluon': 'RSGluonToTT/' + BDiscDirectory + fileConvention
    }
    if not Testing:
        filesets_to_run = {}
        from Filesets import CollectDatasets # Filesets.py reads in .root file address locations and stores all in dictionary called 'filesets'
        filesets = CollectDatasets(Redirector)
        if args.rundataset:
            for a in args.rundataset: # for any dataset included as user argument...
                if args.year > 0:
                    if ('JetHT' in a): 
                        for L in Letters:
                            filesets_to_run[namingConvention+'_JetHT'+L+'_Data'] = filesets[namingConvention+'_JetHT'+L+'_Data'] # include JetHT dataset read in from Filesets
                            SaveLocation[namingConvention+'_JetHT'+L+'_Data'] = 'JetHT/' + BDiscDirectory + fileConvention # file where output will be saved
                    elif ('SingleMu' in a): 
                        filesets_to_run['SingleMu'+str(args.year)+'_Data'] = filesets['SingleMu'+str(args.year)+'_Data'] # include JetHT dataset read in from Filesets
                        SaveLocation['SingleMu'+str(args.year)+'_Data'] = 'SingleMu/' + BDiscDirectory + str(args.year) + '/TTbarRes_0l_' # file where output will be saved
                else: # All Years
                    if ('JetHT' in a): 
                        filesets_to_run[namingConvention+'_JetHT_Data'] = filesets[namingConvention+'JetHT_Data'] # include JetHT dataset read in from Filesets
                        SaveLocation[namingConvention+'_JetHT_Data'] = 'JetHT/' + BDiscDirectory + '/TTbarRes_0l_' # file where output will be saved
                    elif ('SingleMu' in a): 
                        filesets_to_run['SingleMu_Data'] = filesets['SingleMu_Data'] # include JetHT dataset read in from Filesets
                        SaveLocation['SingleMu_Data'] = 'SingleMu/' + BDiscDirectory + '/TTbarRes_0l_' # file where output will be saved
                # Signal MC (then TTbar and QCD MC)
                if 'RSGluon' in a:
                    if a == 'RSGluon':
                        filesets_to_run[namingConvention+'_'+a+'1000'] = filesets[namingConvention+'_'+a+'1000']
                        filesets_to_run[namingConvention+'_'+a+'1500'] = filesets[namingConvention+'_'+a+'1500']
                        filesets_to_run[namingConvention+'_'+a+'2000'] = filesets[namingConvention+'_'+a+'2000']
                        filesets_to_run[namingConvention+'_'+a+'2500'] = filesets[namingConvention+'_'+a+'2500']
                        filesets_to_run[namingConvention+'_'+a+'3000'] = filesets[namingConvention+'_'+a+'3000']
                        filesets_to_run[namingConvention+'_'+a+'3500'] = filesets[namingConvention+'_'+a+'3500']
                        filesets_to_run[namingConvention+'_'+a+'4000'] = filesets[namingConvention+'_'+a+'4000']
                        filesets_to_run[namingConvention+'_'+a+'4500'] = filesets[namingConvention+'_'+a+'4500']
                        filesets_to_run[namingConvention+'_'+a+'5000'] = filesets[namingConvention+'_'+a+'5000']
                        SaveLocation[namingConvention+'_'+a+'1000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'1500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'5000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                    else:
                        filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a]
                elif 'DM' in a:
                    if a == 'DM':
                        filesets_to_run[namingConvention+'_'+a+'1000'] = filesets[namingConvention+'_'+a+'1000']
                        filesets_to_run[namingConvention+'_'+a+'1500'] = filesets[namingConvention+'_'+a+'1500']
                        filesets_to_run[namingConvention+'_'+a+'2000'] = filesets[namingConvention+'_'+a+'2000']
                        filesets_to_run[namingConvention+'_'+a+'2500'] = filesets[namingConvention+'_'+a+'2500']
                        filesets_to_run[namingConvention+'_'+a+'3000'] = filesets[namingConvention+'_'+a+'3000']
                        filesets_to_run[namingConvention+'_'+a+'3500'] = filesets[namingConvention+'_'+a+'3500']
                        filesets_to_run[namingConvention+'_'+a+'4000'] = filesets[namingConvention+'_'+a+'4000']
                        filesets_to_run[namingConvention+'_'+a+'4500'] = filesets[namingConvention+'_'+a+'4500']
                        filesets_to_run[namingConvention+'_'+a+'5000'] = filesets[namingConvention+'_'+a+'5000']
                        SaveLocation[namingConvention+'_'+a+'1000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'1500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'5000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                    else:
                        filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a]
                elif 'TTbar' in a or 'QCD' in a:
                    filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a] # include MC dataset read in from Filesets

        elif args.runMMO:
            for a in args.runMMO: # for any dataset included as user argument...
                if args.year > 0:
                    if ('JetHT' in a): 
                        for L in Letters:
                            filesets_to_run[namingConvention+'_JetHT'+L+'_Data'] = filesets[namingConvention+'_JetHT'+L+'_Data'] # include JetHT dataset read in from Filesets
                            SaveLocation[namingConvention+'_JetHT'+L+'_Data'] = 'JetHT/' + BDiscDirectory + fileConvention # file where output will be saved
                    elif ('SingleMu' in a): 
                        filesets_to_run['SingleMu'+str(args.year)+'_Data'] = filesets['SingleMu'+str(args.year)+'_Data'] # include JetHT dataset read in from Filesets
                        SaveLocation['SingleMu'+str(args.year)+'_Data'] = 'SingleMu/' + BDiscDirectory + str(args.year) + '/TTbarRes_0l_' # file where output will be saved
                else: # All Years
                    if ('JetHT' in a): 
                        filesets_to_run[namingConvention+'_JetHT_Data'] = filesets[namingConvention+'JetHT_Data'] # include JetHT dataset read in from Filesets
                        SaveLocation[namingConvention+'_JetHT_Data'] = 'JetHT/' + BDiscDirectory + '/TTbarRes_0l_' # file where output will be saved
                    elif ('SingleMu' in a): 
                        filesets_to_run['SingleMu_Data'] = filesets['SingleMu_Data'] # include JetHT dataset read in from Filesets
                        SaveLocation['SingleMu_Data'] = 'SingleMu/' + BDiscDirectory + '/TTbarRes_0l_' # file where output will be saved
                # Signal MC (then TTbar and QCD MC)
                if 'RSGluon' in a:
                    if a == 'RSGluon':
                        filesets_to_run[namingConvention+'_'+a+'1000'] = filesets[namingConvention+'_'+a+'1000']
                        filesets_to_run[namingConvention+'_'+a+'1500'] = filesets[namingConvention+'_'+a+'1500']
                        filesets_to_run[namingConvention+'_'+a+'2000'] = filesets[namingConvention+'_'+a+'2000']
                        filesets_to_run[namingConvention+'_'+a+'2500'] = filesets[namingConvention+'_'+a+'2500']
                        filesets_to_run[namingConvention+'_'+a+'3000'] = filesets[namingConvention+'_'+a+'3000']
                        filesets_to_run[namingConvention+'_'+a+'3500'] = filesets[namingConvention+'_'+a+'3500']
                        filesets_to_run[namingConvention+'_'+a+'4000'] = filesets[namingConvention+'_'+a+'4000']
                        filesets_to_run[namingConvention+'_'+a+'4500'] = filesets[namingConvention+'_'+a+'4500']
                        filesets_to_run[namingConvention+'_'+a+'5000'] = filesets[namingConvention+'_'+a+'5000']
                        SaveLocation[namingConvention+'_'+a+'1000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'1500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'5000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                    else:
                        filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a]
                elif 'DM' in a:
                    if a == 'DM':
                        filesets_to_run[namingConvention+'_'+a+'1000'] = filesets[namingConvention+'_'+a+'1000']
                        filesets_to_run[namingConvention+'_'+a+'1500'] = filesets[namingConvention+'_'+a+'1500']
                        filesets_to_run[namingConvention+'_'+a+'2000'] = filesets[namingConvention+'_'+a+'2000']
                        filesets_to_run[namingConvention+'_'+a+'2500'] = filesets[namingConvention+'_'+a+'2500']
                        filesets_to_run[namingConvention+'_'+a+'3000'] = filesets[namingConvention+'_'+a+'3000']
                        filesets_to_run[namingConvention+'_'+a+'3500'] = filesets[namingConvention+'_'+a+'3500']
                        filesets_to_run[namingConvention+'_'+a+'4000'] = filesets[namingConvention+'_'+a+'4000']
                        filesets_to_run[namingConvention+'_'+a+'4500'] = filesets[namingConvention+'_'+a+'4500']
                        filesets_to_run[namingConvention+'_'+a+'5000'] = filesets[namingConvention+'_'+a+'5000']
                        SaveLocation[namingConvention+'_'+a+'1000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'1500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'5000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                    else:
                        filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a]
                elif 'TTbar' in a or 'QCD' in a:
                    filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a] # include MC dataset read in from Filesets

        elif args.runAMO:
            for a in args.runAMO: # for any dataset included as user argument...
                if args.year > 0:
                    if ('JetHT' in a): 
                        for L in Letters:
                            filesets_to_run[namingConvention+'_JetHT'+L+'_Data'] = filesets[namingConvention+'_JetHT'+L+'_Data'] # include JetHT dataset read in from Filesets
                            SaveLocation[namingConvention+'_JetHT'+L+'_Data'] = 'JetHT/' + BDiscDirectory + fileConvention # file where output will be saved
                    elif ('SingleMu' in a): 
                        filesets_to_run['SingleMu'+str(args.year)+'_Data'] = filesets['SingleMu'+str(args.year)+'_Data'] # include JetHT dataset read in from Filesets
                        SaveLocation['SingleMu'+str(args.year)+'_Data'] = 'SingleMu/' + BDiscDirectory + str(args.year) + '/TTbarRes_0l_' # file where output will be saved
                else: # All Years
                    if ('JetHT' in a): 
                        filesets_to_run[namingConvention+'_JetHT_Data'] = filesets[namingConvention+'JetHT_Data'] # include JetHT dataset read in from Filesets
                        SaveLocation[namingConvention+'_JetHT_Data'] = 'JetHT/' + BDiscDirectory + '/TTbarRes_0l_' # file where output will be saved
                    elif ('SingleMu' in a): 
                        filesets_to_run['SingleMu_Data'] = filesets['SingleMu_Data'] # include JetHT dataset read in from Filesets
                        SaveLocation['SingleMu_Data'] = 'SingleMu/' + BDiscDirectory + '/TTbarRes_0l_' # file where output will be saved
                # Signal MC (then TTbar and QCD MC)
                if 'RSGluon' in a:
                    if a == 'RSGluon':
                        filesets_to_run[namingConvention+'_'+a+'1000'] = filesets[namingConvention+'_'+a+'1000']
                        filesets_to_run[namingConvention+'_'+a+'1500'] = filesets[namingConvention+'_'+a+'1500']
                        filesets_to_run[namingConvention+'_'+a+'2000'] = filesets[namingConvention+'_'+a+'2000']
                        filesets_to_run[namingConvention+'_'+a+'2500'] = filesets[namingConvention+'_'+a+'2500']
                        filesets_to_run[namingConvention+'_'+a+'3000'] = filesets[namingConvention+'_'+a+'3000']
                        filesets_to_run[namingConvention+'_'+a+'3500'] = filesets[namingConvention+'_'+a+'3500']
                        filesets_to_run[namingConvention+'_'+a+'4000'] = filesets[namingConvention+'_'+a+'4000']
                        filesets_to_run[namingConvention+'_'+a+'4500'] = filesets[namingConvention+'_'+a+'4500']
                        filesets_to_run[namingConvention+'_'+a+'5000'] = filesets[namingConvention+'_'+a+'5000']
                        SaveLocation[namingConvention+'_'+a+'1000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'1500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'5000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                    else:
                        filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a]
                elif 'DM' in a:
                    if a == 'DM':
                        filesets_to_run[namingConvention+'_'+a+'1000'] = filesets[namingConvention+'_'+a+'1000']
                        filesets_to_run[namingConvention+'_'+a+'1500'] = filesets[namingConvention+'_'+a+'1500']
                        filesets_to_run[namingConvention+'_'+a+'2000'] = filesets[namingConvention+'_'+a+'2000']
                        filesets_to_run[namingConvention+'_'+a+'2500'] = filesets[namingConvention+'_'+a+'2500']
                        filesets_to_run[namingConvention+'_'+a+'3000'] = filesets[namingConvention+'_'+a+'3000']
                        filesets_to_run[namingConvention+'_'+a+'3500'] = filesets[namingConvention+'_'+a+'3500']
                        filesets_to_run[namingConvention+'_'+a+'4000'] = filesets[namingConvention+'_'+a+'4000']
                        filesets_to_run[namingConvention+'_'+a+'4500'] = filesets[namingConvention+'_'+a+'4500']
                        filesets_to_run[namingConvention+'_'+a+'5000'] = filesets[namingConvention+'_'+a+'5000']
                        SaveLocation[namingConvention+'_'+a+'1000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'1500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'5000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                    else:
                        filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a]
                elif 'TTbar' in a or 'QCD' in a:
                    filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a] # include MC dataset read in from Filesets

        elif args.runflavoreff:
            for a in args.runflavoreff: # for any dataset included as user argument...
                if 'RSGluon' in a:
                    if a == 'RSGluon':
                        filesets_to_run[namingConvention+'_'+a+'1000'] = filesets[namingConvention+'_'+a+'1000']
                        filesets_to_run[namingConvention+'_'+a+'1500'] = filesets[namingConvention+'_'+a+'1500']
                        filesets_to_run[namingConvention+'_'+a+'2000'] = filesets[namingConvention+'_'+a+'2000']
                        filesets_to_run[namingConvention+'_'+a+'2500'] = filesets[namingConvention+'_'+a+'2500']
                        filesets_to_run[namingConvention+'_'+a+'3000'] = filesets[namingConvention+'_'+a+'3000']
                        filesets_to_run[namingConvention+'_'+a+'3500'] = filesets[namingConvention+'_'+a+'3500']
                        filesets_to_run[namingConvention+'_'+a+'4000'] = filesets[namingConvention+'_'+a+'4000']
                        filesets_to_run[namingConvention+'_'+a+'4500'] = filesets[namingConvention+'_'+a+'4500']
                        filesets_to_run[namingConvention+'_'+a+'5000'] = filesets[namingConvention+'_'+a+'5000']
                        SaveLocation[namingConvention+'_'+a+'1000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'1500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4500'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'5000'] = 'RSGluonToTT/' + BDiscDirectory + fileConvention
                    else:
                        filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a]
                elif 'DM' in a:
                    if a == 'DM':
                        filesets_to_run[namingConvention+'_'+a+'1000'] = filesets[namingConvention+'_'+a+'1000']
                        filesets_to_run[namingConvention+'_'+a+'1500'] = filesets[namingConvention+'_'+a+'1500']
                        filesets_to_run[namingConvention+'_'+a+'2000'] = filesets[namingConvention+'_'+a+'2000']
                        filesets_to_run[namingConvention+'_'+a+'2500'] = filesets[namingConvention+'_'+a+'2500']
                        filesets_to_run[namingConvention+'_'+a+'3000'] = filesets[namingConvention+'_'+a+'3000']
                        filesets_to_run[namingConvention+'_'+a+'3500'] = filesets[namingConvention+'_'+a+'3500']
                        filesets_to_run[namingConvention+'_'+a+'4000'] = filesets[namingConvention+'_'+a+'4000']
                        filesets_to_run[namingConvention+'_'+a+'4500'] = filesets[namingConvention+'_'+a+'4500']
                        filesets_to_run[namingConvention+'_'+a+'5000'] = filesets[namingConvention+'_'+a+'5000']
                        SaveLocation[namingConvention+'_'+a+'1000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'1500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'2500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'3500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'4500'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                        SaveLocation[namingConvention+'_'+a+'5000'] = 'ZprimeDMToTTbar/' + BDiscDirectory + fileConvention
                    else:
                        filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a]
                elif 'TTbar' in a or 'QCD' in a:
                    filesets_to_run[namingConvention+'_'+a] = filesets[namingConvention+'_'+a] # include MC dataset read in from Filesets
        elif args.runmistag: # if args.mistag: Only run 1st uproot job for ttbar and data to get mistag rate with tt contamination removed
            if args.mistagcorrect:
                filesets_to_run[namingConvention+'_TTbar'] = filesets[namingConvention+'_TTbar']
            if args.year > 0:
                for L in Letters:
                    filesets_to_run[namingConvention+'_JetHT'+L+'_Data'] = filesets[namingConvention+'_JetHT'+L+'_Data'] # include JetHT dataset read in from Filesets
                    SaveLocation[namingConvention+'_JetHT'+L+'_Data'] = 'JetHT/' + BDiscDirectory + fileConvention # file where output will be saved
            else:
                filesets_to_run[namingConvention+'_JetHT_Data'] = filesets[namingConvention+'JetHT_Data'] # include JetHT dataset read in from Filesets
                SaveLocation[namingConvention+'_JetHT_Data'] = 'JetHT/' + BDiscDirectory + '/TTbarRes_0l_' # file where output will be saved
        elif isTrigEffArg: # just run over data
            if args.year > 0:
                filesets_to_run['SingleMu'+str(args.year)+'_Data'] = filesets['SingleMu'+str(args.year)+'_Data']
                SaveLocation['SingleMu'+str(args.year)+'_Data'] = 'SingleMu/' + BDiscDirectory + str(args.year) + '/TTbarRes_0l_'
            else:
                filesets_to_run['SingleMu_Data'] = filesets['SingleMu_Data']
                SaveLocation['SingleMu_Data'] = 'SingleMu/' + BDiscDirectory + '/TTbarRes_0l_'
        else: # if somehow, the initial needed arguments are not used
            print("Something is wrong.  Please come and investigate what the problem could be")
    else:
        TestRootFiles = ['']
        filesets = {
            'TestSample_ttbarRES':TestRootFiles
        }
        filesets_forweights = filesets

    #    ---------------------------------------------------------------------------
    #    DDDD       A      SSSSS K     K       SSSSS EEEEEEE TTTTTTT U     U PPPPPP      
    #    D   D     A A    S      K   K        S      E          T    U     U P     P     
    #    D    D   A   A  S       K K         S       E          T    U     U P     P     
    #    D     D  AAAAA   SSSSS  KKk          SSSSS  EEEEEEE    T    U     U PPPPPP      
    #    D    D  A     A       S K  K              S E          T    U     U P           
    #    D   D   A     A      S  K   K            S  E          T     U   U  P           
    #    DDDD    A     A SSSSS   K   K       SSSSS   EEEEEEE    T      UUU   P    
    #    ---------------------------------------------------------------------------

    # client = None
    # cluster = None

    if UsingDaskExecutor == True and args.casa:
        from dask.distributed import Client #, Scheduler, SchedulerPlugin
        from dask.distributed.diagnostics.plugin import UploadDirectory
        from coffea_casa import CoffeaCasaCluster

        if __name__ == "__main__":       

            cluster = None
            uploadDir = 'TTbarAllHadUproot'#/CoffeaOutputsForCombine/Coffea_firstRun'

            if args.newCluster:
                cluster = CoffeaCasaCluster(cores=7, memory="5 GiB", death_timeout=TimeOut)
                cluster.adapt(minimum=1, maximum=14)
            else:
                cluster = 'tls://ac-2emalik-2ewilliams-40cern-2ech.dask.cmsaf-prod.flatiron.hollandhpc.org:8786'

            client = Client(cluster)

            try:
                client.register_worker_plugin(UploadDirectory(uploadDir,restart=True,update_path=True),nanny=True)
            except OSError as ose:
                print('\n', ose)    
                print('\nFor some reason, Dask did not work as intended\n')
                exit
                if args.newCluster:
                    cluster.close()

            # print('All Hidden Directories:\n')
            # print(client.run(os.listdir))
            # print('Look inside dask-worker-space:\n')
            # print(client.run(os.listdir,"dask-worker-space"))
            # # print('Look inside dask-worker-space/purge.lock:\n')
            # # print(client.run(os.listdir,"dask-worker-space/purge.lock"))
            # print('Look inside TTbarAllHadUproot:\n')
            # print(client.run(os.listdir,"dask-worker-space/TTbarAllHadUproot"))


    elif UsingDaskExecutor == True and args.lpc:
        from dask.distributed import Client #, Scheduler, SchedulerPlugin
        from dask.distributed.diagnostics.plugin import UploadDirectory
        from lpcjobqueue import LPCCondorCluster

        if __name__ == "__main__":  

            cluster = LPCCondorCluster(death_timeout=TimeOut)
            cluster.adapt(minimum=1, maximum=10)
            client = Client(cluster)

            try:
                client.register_worker_plugin(UploadDirectory('TTbarAllHadUproot',restart=True,update_path=True),nanny=True)
            except OSError as ose:
                print('\n', ose)

            # client.restart()
            # client.upload_file('TTbarAllHadUproot/Filesets.py')
            # client.upload_file('TTbarAllHadUproot/TTbarResProcessor.py')
            # client.upload_file('TTbarAllHadUproot/TTbarResLookUpTables.py')

    elif UsingDaskExecutor == True and args.winterfell:
        from dask.distributed import Client
        from dask.distributed.diagnostics.plugin import UploadDirectory
        import shutil
        
        if __name__ == "__main__":       

            # cluster = '128.205.11.158:8787'
            # uploadDir = '/mnt/users/acwillia/TTbarAllHadUproot'
            client = Client()
            if (args.runMMO or args.runAMO or args.uproot == 2):
                shutil.make_archive('UploadToDask', 'zip', 'TTbarAllHadUproot')
                print('archive made')
                print('Uploading archive to client...')
                client.upload_file('UploadToDask.zip')
                print('Archive uploaded')
            # try:
            #     client.register_worker_plugin(UploadDirectory(uploadDir,restart=True,update_path=True),nanny=True)
            # except OSError as ose:
            #     print('\n', ose)    
            #     print('\nFor some reason, Dask did not work as intended\n')
            #     exit
            #     if args.newCluster:
            #         cluster.close()

            # print('Worker Directories:\n')
            # # print(client.run(os.listdir))
            # print(client.run(os.listdir,"/mnt/users/acwillia/TTbarAllHadUproot"))

    #    ----------------------------------------------------------------------------------------------------  
    #    U     U PPPPPP  RRRRRR    OOO     OOO   TTTTTTT     FFFFFFF L          A    V     V   OOO   RRRRRR      
    #    U     U P     P R     R  O   O   O   O     T        F       L         A A   V     V  O   O  R     R     
    #    U     U P     P R     R O     O O     O    T        F       L        A   A  V     V O     O R     R     
    #    U     U PPPPPP  RRRRRR  O     O O     O    T        FFFFFFF L        AAAAA  V     V O     O RRRRRR      
    #    U     U P       R   R   O     O O     O    T        F       L       A     A  V   V  O     O R   R       
    #     U   U  P       R    R   O   O   O   O     T        F       L       A     A   V V    O   O  R    R      
    #      UUU   P       R     R   OOO     OOO      T        F       LLLLLLL A     A    V      OOO   R     R   
    #    ----------------------------------------------------------------------------------------------------  

    if args.runflavoreff:
        tstart = time.time()

        outputs_unweighted = {}

        seed = 1234577890
        prng = RandomState(seed)

        for name,files in filesets_to_run.items(): 
            print('Processing', name, '...')
            if not RunAllRootFiles:
                if not UsingDaskExecutor:
                    chosen_exec = 'futures'
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=MCFlavorEfficiencyProcessor(RandomDebugMode=False,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           bdisc=BDisc,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.futures_executor,
                                                      executor_args={
                                                          #'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema, #NanoAODSchema,
                                                          'workers': 2},
                                                      chunksize=Chunk[0], maxchunks=Chunk[1])
                else: # use dask
                    chosen_exec = 'dask'
                    client.wait_for_workers(n_workers=1, timeout=TimeOut)
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=MCFlavorEfficiencyProcessor(RandomDebugMode=False,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           bdisc=BDisc,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.dask_executor,
                                                      executor_args={
                                                          'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema},
                                                      chunksize=Chunk[0], maxchunks=Chunk[1])
                    # client.restart()

                elapsed = time.time() - tstart
                outputs_unweighted[name] = output
                print(output)

                if args.saveFlav:
                    mkdir_p('TTbarAllHadUproot/CoffeaOutputsForMCFlavorAnalysis/'
                              + SaveLocation[name])

                    savefilename = 'TTbarAllHadUproot/CoffeaOutputsForMCFlavorAnalysis/' + SaveLocation[name] + name     + '_MCFlavorAnalysis'  + OldDisc + '.coffea'
                    util.save(output, savefilename)
                    print('saving ' + savefilename)


            else: # Run all Root Files
                if not UsingDaskExecutor:
                    chosen_exec = 'futures'
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=MCFlavorEfficiencyProcessor(RandomDebugMode=False,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           bdisc=BDisc,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.futures_executor,
                                                      executor_args={
                                                          #'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema, #NanoAODSchema,
                                                          'workers': 2})

                else: # use dask
                    chosen_exec = 'dask'
                    client.wait_for_workers(n_workers=1, timeout=TimeOut)
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=MCFlavorEfficiencyProcessor(RandomDebugMode=False,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           bdisc=BDisc,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.dask_executor,
                                                      executor_args={
                                                          'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema})
                    # client.restart()

                elapsed = time.time() - tstart
                outputs_unweighted[name] = output
                print(output)

                if args.saveFlav:
                    mkdir_p('TTbarAllHadUproot/CoffeaOutputsForMCFlavorAnalysis/'
                              + SaveLocation[name])

                    savefilename = 'TTbarAllHadUproot/CoffeaOutputsForMCFlavorAnalysis/' + SaveLocation[name] + name + '_MCFlavorAnalysis' + OldDisc + '.coffea'
                    util.save(output, savefilename)
                    print('saving ' + savefilename)


            print('Elapsed time = ', elapsed, ' sec.')
            print('Elapsed time = ', elapsed/60., ' min.')
            print('Elapsed time = ', elapsed/3600., ' hrs.') 

        for dataset,output in outputs_unweighted.items(): 
            print("-------Unweighted " + dataset + "--------")
            for i,j in output['cutflow'].items():        
                print( '%20s : %1s' % (i,j) ) 

            FlavEffList('b', output, dataset, BDiscDirectory, args.saveFlav)
            FlavEffList('c', output, dataset, BDiscDirectory, args.saveFlav)
            FlavEffList('udsg', output, dataset, BDiscDirectory, args.saveFlav)
            print("\n\nWe\'re done here\n!!")
        if args.dask and args.newCluster:    
            cluster.close()
        print(psutil.Process(os.getpid()).memory_info().rss / 10 ** 6) # Display MB of memory usage
        exit() # No need to go further if performing trigger analysis


    #    -----------------------------------------------------------------------------------------------------------
    #    U     U PPPPPP  RRRRRR    OOO     OOO   TTTTTTT     TTTTTTT RRRRRR  IIIIIII GGGGGGG GGGGGGG EEEEEEE RRRRRR      
    #    U     U P     P R     R  O   O   O   O     T           T    R     R    I    G       G       E       R     R     
    #    U     U P     P R     R O     O O     O    T           T    R     R    I    G       G       E       R     R     
    #    U     U PPPPPP  RRRRRR  O     O O     O    T           T    RRRRRR     I    G  GGGG G  GGGG EEEEEEE RRRRRR      
    #    U     U P       R   R   O     O O     O    T           T    R   R      I    G     G G     G E       R   R       
    #     U   U  P       R    R   O   O   O   O     T           T    R    R     I    G     G G     G E       R    R      
    #      UUU   P       R     R   OOO     OOO      T           T    R     R IIIIIII  GGGGG   GGGGG  EEEEEEE R     R       
    #    -----------------------------------------------------------------------------------------------------------


    if isTrigEffArg:
        tstart = time.time()

        outputs_unweighted = {}

        seed = 1234577890
        prng = RandomState(seed)

        for name,files in filesets_to_run.items(): 
            print('Processing', name, '...')
            if not RunAllRootFiles:
                if not UsingDaskExecutor:
                    chosen_exec = 'futures'
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TriggerAnalysisProcessor(RandomDebugMode=False,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.futures_executor,
                                                      executor_args={
                                                          #'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema, #NanoAODSchema,
                                                          'workers': 2},
                                                      chunksize=Chunk[0], maxchunks=Chunk[1])
                else: # use dask
                    chosen_exec = 'dask'
                    client.wait_for_workers(n_workers=1, timeout=TimeOut)
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TriggerAnalysisProcessor(RandomDebugMode=False,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.dask_executor,
                                                      executor_args={
                                                          'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema},
                                                      chunksize=Chunk[0], maxchunks=Chunk[1])
                    # client.restart()

                elapsed = time.time() - tstart
                outputs_unweighted[name] = output
                print(output)

                if args.saveTrig:
                    mkdir_p('TTbarAllHadUproot/CoffeaOutputsForTriggerAnalysis/'
                              + SaveLocation[name])
                    savefilename = 'TTbarAllHadUproot/CoffeaOutputsForTriggerAnalysis/' + SaveLocation[name] + name + '_TriggerAnalysis' + OldDisc + '.coffea'
                    util.save(output, savefilename)
                    print('saving ' + savefilename)


            else: # Run all Root Files
                if not UsingDaskExecutor:
                    chosen_exec = 'futures'
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TriggerAnalysisProcessor(RandomDebugMode=False,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.futures_executor,
                                                      executor_args={
                                                          #'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema, #NanoAODSchema,
                                                          'workers': 2})

                else: # use dask
                    chosen_exec = 'dask'
                    client.wait_for_workers(n_workers=1, timeout=TimeOut)
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TriggerAnalysisProcessor(RandomDebugMode=False,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.dask_executor,
                                                      executor_args={
                                                          'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema})
                    # client.restart()

                elapsed = time.time() - tstart
                outputs_unweighted[name] = output
                print(output)

                if args.saveTrig:
                    mkdir_p('TTbarAllHadUproot/CoffeaOutputsForTriggerAnalysis/'
                              + SaveLocation[name])
                    savefilename =  output, 'TTbarAllHadUproot/CoffeaOutputsForTriggerAnalysis/' + SaveLocation[name] + name + '_TriggerAnalysis' + OldDisc + '.coffea'
                    util.save(output, savefilename)
                    print('saving ' + savefilename)


            print('Elapsed time = ', elapsed, ' sec.')
            print('Elapsed time = ', elapsed/60., ' min.')
            print('Elapsed time = ', elapsed/3600., ' hrs.') 

        for name,output in outputs_unweighted.items(): 
            print("-------Unweighted " + name + "--------")
            for i,j in output['cutflow'].items():        
                print( '%20s : %1s' % (i,j) )
        print("\n\nWe\'re done here\n!!")
        if args.dask and args.newCluster:
            cluster.close()
            print('\nManual Cluster Closed\n')
        print(psutil.Process(os.getpid()).memory_info().rss / 10 ** 6) # Display MB of memory usage
        exit() # No need to go further if performing trigger analysis
    else:
        pass

    #    ---------------------------------------------------------------------------
    #    U     U PPPPPP  RRRRRR    OOO     OOO   TTTTTTT       OOO   N     N EEEEEEE     
    #    U     U P     P R     R  O   O   O   O     T         O   O  NN    N E           
    #    U     U P     P R     R O     O O     O    T        O     O N N   N E           
    #    U     U PPPPPP  RRRRRR  O     O O     O    T        O     O N  N  N EEEEEEE     
    #    U     U P       R   R   O     O O     O    T        O     O N   N N E           
    #     U   U  P       R    R   O   O   O   O     T         O   O  N    NN E           
    #      UUU   P       R     R   OOO     OOO      T          OOO   N     N EEEEEEE  
    #    ---------------------------------------------------------------------------

    tstart = time.time()

    outputs_unweighted = {}

    seed = 1234577890
    prng = RandomState(seed)

    for name,files in filesets_to_run.items(): 
        print('\n\n' + name + '\n\n-----------------------------------------------------')
        if not LoadingUnweightedFiles:
            print('Processing', name, '...')
            if not RunAllRootFiles:
                if not UsingDaskExecutor:
                    chosen_exec = 'futures'
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TTbarResProcessor(UseLookUpTables=False,
                                                                                           ModMass=False, 
                                                                                           RandomDebugMode=False,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           # triggerAnalysisObjects = isTrigEffArg,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.futures_executor,
                                                      executor_args={
                                                          #'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema, #NanoAODSchema,
                                                          'workers': 2},
                                                      chunksize=Chunk[0], maxchunks=Chunk[1])
                else: # use dask
                    chosen_exec = 'dask'
                    client.wait_for_workers(n_workers=1, timeout=TimeOut)
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TTbarResProcessor(UseLookUpTables=False,
                                                                                           ModMass=False, 
                                                                                           RandomDebugMode=False,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           # triggerAnalysisObjects = isTrigEffArg,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.dask_executor,
                                                      executor_args={
                                                          'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema},
                                                      chunksize=Chunk[0], maxchunks=Chunk[1])
                    # client.restart()

                elapsed = time.time() - tstart
                outputs_unweighted[name] = output
                print(output)
                if SaveFirstRun:
                    mkdir_p('TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_FirstRun/'
                              + SaveLocation[name])

                    savefilename = 'TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_FirstRun/' + SaveLocation[name] + name + OldDisc + '.coffea'
                    util.save(output, savefilename)
                    print('saving ' + savefilename)                           


            else: # Run all Root Files
                if not UsingDaskExecutor:
                    chosen_exec = 'futures'
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TTbarResProcessor(UseLookUpTables=False,
                                                                                           ModMass=False, 
                                                                                           RandomDebugMode=False,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           # triggerAnalysisObjects = isTrigEffArg,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.futures_executor,
                                                      executor_args={
                                                          #'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema, #NanoAODSchema,
                                                          'workers': 2})

                else: # use dask
                    chosen_exec = 'dask'
                    client.wait_for_workers(n_workers=1, timeout=TimeOut)
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TTbarResProcessor(UseLookUpTables=False,
                                                                                           ModMass=False, 
                                                                                           RandomDebugMode=False,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           # triggerAnalysisObjects = isTrigEffArg,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.dask_executor,
                                                      executor_args={
                                                          'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema})
                    # client.restart()

                elapsed = time.time() - tstart
                outputs_unweighted[name] = output
                print(output)
                if SaveFirstRun:
                    mkdir_p('TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_FirstRun/'
                              + SaveLocation[name])


                    savefilename = 'TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_FirstRun/' + SaveLocation[name] + name + OldDisc + '.coffea'                         
                    util.save(output, savefilename)
                    print('saving ' + savefilename)

            for name,output in outputs_unweighted.items(): 
                print("-------Unweighted " + name + "--------")
                for i,j in output['cutflow'].items():        
                    print( '%20s : %1s' % (i,j) )

        else: # Load files
            output = util.load('TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_FirstRun/'
                               + SaveLocation[name]
                               + name 
                               + OldDisc
                               + '.coffea')

            outputs_unweighted[name] = output
            print(name + ' unweighted output loaded')
            elapsed = time.time() - tstart

        print('Elapsed time = ', elapsed, ' sec.')
        print('Elapsed time = ', elapsed/60., ' min.')
        print('Elapsed time = ', elapsed/3600., ' hrs.') 


    #    -----------------------------------------------------------------------------------
    #    GGGGGGG EEEEEEE TTTTTTT     M     M IIIIIII   SSSSS TTTTTTT    A    GGGGGGG   SSSSS     
    #    G       E          T        MM   MM    I     S         T      A A   G        S          
    #    G       E          T        M M M M    I    S          T     A   A  G       S           
    #    G  GGGG EEEEEEE    T        M  M  M    I     SSSSS     T     AAAAA  G  GGGG  SSSSS      
    #    G     G E          T        M     M    I          S    T    A     A G     G       S     
    #    G     G E          T        M     M    I         S     T    A     A G     G      S      
    #     GGGGG  EEEEEEE    T        M     M IIIIIII SSSSS      T    A     A  GGGGG  SSSSS  
    #    -----------------------------------------------------------------------------------

    import TTbarResLookUpTables

    from TTbarResLookUpTables import CreateLUTS, LoadDataLUTS #, CreateMCEfficiencyLUTS

    mistag_luts = None

    if args.runmistag:
        CreateLUTS(filesets_to_run, outputs_unweighted, BDiscDirectory, args.year, VFP, args.mistagcorrect, Letters, args.saveMistag)
        mistag_luts = LoadDataLUTS(BDiscDirectory, args.year, VFP, args.mistagcorrect, Letters) # Specifically get data mistag rates
    else:
        mistag_luts = LoadDataLUTS(BDiscDirectory, args.year, VFP, args.mistagcorrect, Letters)

    if OnlyCreateLookupTables:
        print("\n\nWe\'re done here!!\n")
        if args.dask and args.newCluster:
            cluster.close()
        print(psutil.Process(os.getpid()).memory_info().rss / 10 ** 6) # Display MB of memory usage
        exit()



    """ Second uproot job runs the processor with the mistag rates (and flavor effs if desired) and Mass-Modification Procedure """

    #    ---------------------------------------------------------------------------
    #    U     U PPPPPP  RRRRRR    OOO     OOO   TTTTTTT     TTTTTTT W     W   OOO       
    #    U     U P     P R     R  O   O   O   O     T           T    W     W  O   O      
    #    U     U P     P R     R O     O O     O    T           T    W     W O     O     
    #    U     U PPPPPP  RRRRRR  O     O O     O    T           T    W  W  W O     O     
    #    U     U P       R   R   O     O O     O    T           T    W W W W O     O     
    #     U   U  P       R    R   O   O   O   O     T           T    WW   WW  O   O      
    #      UUU   P       R     R   OOO     OOO      T           T    W     W   OOO    
    #    ---------------------------------------------------------------------------

    tstart = time.time()

    outputs_weighted = {}

    seed = 1234577890
    prng = RandomState(seed)

    if not OnlyCreateLookupTables and (not args.runMMO and not args.runAMO):
        for name,files in filesets_to_run.items(): 
            print('Processing', name)
            if not RunAllRootFiles:
                if not UsingDaskExecutor:
                    chosen_exec = 'futures'
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                           lu=mistag_luts,
                                                                                           ModMass=True, 
                                                                                           RandomDebugMode=False,
                                                                                           BDirect = BDiscDirectory,
                                                                                           xsSystematicWeight = xsSystwgt,
                                                                                           lumSystematicWeight = lumSystwgt,
                                                                                           ApplyTopReweight = args.tpt,
                                                                                           ApplybtagSF=ApplybSF,
                                                                                           ApplyJes=ApplyJES,
                                                                                           var=var,
                                                                                           ApplyPdf=ApplyPDF,
                                                                                           ApplyPrefiring = ApplyPrefiring,
                                                                                           ApplyPUweights = ApplyPUweights,
                                                                                           sysType=SystType,
                                                                                           ScaleFactorFile=SFfile,
                                                                                           UseEfficiencies=args.useEff,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           eras=Letters,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      #executor=processor.iterative_executor,
                                                      executor=processor.futures_executor,
                                                      executor_args={
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema, #NanoAODSchema,
                                                          'workers': 2},
                                                      chunksize=Chunk[0], maxchunks=Chunk[1])
                else:
                    chosen_exec = 'dask'
                    client.wait_for_workers(n_workers=1, timeout=TimeOut)
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                           lu=mistag_luts,
                                                                                           extraDaskDirectory = daskDirectory,
                                                                                           ModMass=True, 
                                                                                           RandomDebugMode=False,
                                                                                           BDirect = BDiscDirectory,
                                                                                           xsSystematicWeight = xsSystwgt,
                                                                                           lumSystematicWeight = lumSystwgt,
                                                                                           ApplyTopReweight = args.tpt,
                                                                                           ApplybtagSF=ApplybSF,
                                                                                           ApplyJes=ApplyJES,
                                                                                           var=var,
                                                                                           ApplyPdf=ApplyPDF,
                                                                                           ApplyPrefiring = ApplyPrefiring,
                                                                                           ApplyPUweights = ApplyPUweights,
                                                                                           sysType=SystType,
                                                                                           ScaleFactorFile=SFfile,
                                                                                           UseEfficiencies=args.useEff,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           eras=Letters,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.dask_executor,
                                                      executor_args={
                                                          'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema,
                                                          'heavy_input': 'TTbarResCoffea/data',
                                                          'function_name': 'correctionlib.CorrectionSet.from_file'},
                                                      chunksize=Chunk[0], maxchunks=Chunk[1])
                    # client.restart()
                elapsed = time.time() - tstart
                outputs_weighted[name] = output
                print(output)
                if SaveSecondRun:
                    mkdir_p('TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/'
                              + SaveLocation[name])

                    savefilename = 'TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/' + SaveLocation[name] + name  + '_weighted' + UncType + SystType + method + TPT + OldDisc + '.coffea'                       
                    util.save(output, savefilename)
                    print('saving ' + savefilename)                          


            else: # Run all Root Files
                if not UsingDaskExecutor:
                    chosen_exec = 'futures'
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                           lu=mistag_luts,
                                                                                           ModMass=True, 
                                                                                           RandomDebugMode=False,
                                                                                           BDirect = BDiscDirectory,
                                                                                           xsSystematicWeight = xsSystwgt,
                                                                                           lumSystematicWeight = lumSystwgt,
                                                                                           ApplyTopReweight = args.tpt,
                                                                                           ApplybtagSF=ApplybSF,
                                                                                           ApplyJes=ApplyJES,
                                                                                           var=var,
                                                                                           ApplyPdf=ApplyPDF,
                                                                                           ApplyPrefiring = ApplyPrefiring,
                                                                                           ApplyPUweights = ApplyPUweights,
                                                                                           sysType=SystType,
                                                                                           ScaleFactorFile=SFfile,
                                                                                           UseEfficiencies=args.useEff,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           eras=Letters,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      #executor=processor.iterative_executor,
                                                      executor=processor.futures_executor,
                                                      executor_args={
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema, #NanoAODSchema,
                                                          'workers': 2})

                else:
                    chosen_exec = 'dask'
                    client.wait_for_workers(n_workers=1, timeout=TimeOut)
                    output = processor.run_uproot_job({name:files},
                                                      treename='Events',
                                                      processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                           lu=mistag_luts,
                                                                                           extraDaskDirectory = daskDirectory,
                                                                                           ModMass=True, 
                                                                                           RandomDebugMode=False,
                                                                                           BDirect = BDiscDirectory,
                                                                                           xsSystematicWeight = xsSystwgt,
                                                                                           lumSystematicWeight = lumSystwgt,
                                                                                           ApplyTopReweight = args.tpt,
                                                                                           ApplybtagSF=ApplybSF,
                                                                                           ApplyJes=ApplyJES,
                                                                                           var=var,
                                                                                           ApplyPrefiring = ApplyPrefiring,
                                                                                           sysType=SystType,
                                                                                           ScaleFactorFile=SFfile,
                                                                                           UseEfficiencies=args.useEff,
                                                                                           bdisc = BDisc,
                                                                                           year=args.year,
                                                                                           apv=convertLabel[VFP],
                                                                                           vfp=VFP,
                                                                                           eras=Letters,
                                                                                           trigs_to_run=Trigs_to_run,
                                                                                           prng=prng),
                                                      executor=processor.dask_executor,
                                                      executor_args={
                                                          'client': client,
                                                          'skipbadfiles':False,
                                                          'schema': BaseSchema})
                    # client.restart()
                elapsed = time.time() - tstart
                outputs_weighted[name] = output
                print(output)
                if SaveSecondRun:
                    mkdir_p('TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/'
                              + SaveLocation[name])


                    savefilename = 'TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/' + SaveLocation[name] + name  + '_weighted' + UncType + SystType + method + TPT + OldDisc + '.coffea'                       
                    util.save(output, savefilename)
                    print('saving ' + savefilename)  
            print('Elapsed time = ', elapsed, ' sec.')
            print('Elapsed time = ', elapsed/60., ' min.')
            print('Elapsed time = ', elapsed/3600., ' hrs.') 

        for name,output in outputs_weighted.items(): 
            print("-------Weighted " + name + "--------")
            for i,j in output['cutflow'].items():        
                print( '%20s : %1s' % (i,j) )
        print("\n\nWe\'re done here!!\n")
        if args.dask:
            cluster.close()
        print(psutil.Process(os.getpid()).memory_info().rss / 10 ** 6) # Display MB of memory usage
        exit()
    # else:
    #     print("\n\nWe\'re done here!!\n")
    #     if args.dask and args.newCluster:
    #         cluster.close()
    #     exit()




    #    ----------------------------------------------------------------------------    
    #     U     U PPPPPP  RRRRRR    OOO     OOO   TTTTTTT     M     M M     M   OOO       
    #     U     U P     P R     R  O   O   O   O     T        MM   MM MM   MM  O   O      
    #     U     U P     P R     R O     O O     O    T        M M M M M M M M O     O     
    #     U     U PPPPPP  RRRRRR  O     O O     O    T        M  M  M M  M  M O     O     
    #     U     U P       R   R   O     O O     O    T        M     M M     M O     O     
    #      U   U  P       R    R   O   O   O   O     T        M     M M     M  O   O      
    #       UUU   P       R     R   OOO     OOO      T        M     M M     M   OOO 
    #    ----------------------------------------------------------------------------

    if args.runMMO:
        tstart = time.time()

        outputs_weighted = {}

        seed = 1234577890
        prng = RandomState(seed)

        for name,files in filesets_to_run.items(): 
            if not OnlyCreateLookupTables:
                print('Processing', name)
                if not RunAllRootFiles:
                    if not UsingDaskExecutor:
                        chosen_exec = 'futures'
                        output = processor.run_uproot_job({name:files},
                                                          treename='Events',
                                                          processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                               lu=mistag_luts,
                                                                                               ModMass=True, 
                                                                                               RandomDebugMode=False,
                                                                                               BDirect = BDiscDirectory,
                                                                                               bdisc = BDisc,
                                                                                               year=args.year,
                                                                                               apv=convertLabel[VFP],
                                                                                               vfp=VFP,
                                                                                               eras=Letters,
                                                                                               trigs_to_run=Trigs_to_run,
                                                                                               prng=prng),
                                                          #executor=processor.iterative_executor,
                                                          executor=processor.futures_executor,
                                                          executor_args={
                                                              'skipbadfiles':False,
                                                              'schema': BaseSchema, #NanoAODSchema,
                                                              'workers': 2},
                                                          chunksize=Chunk[0], maxchunks=Chunk[1])
                    else:
                        chosen_exec = 'dask'
                        client.wait_for_workers(n_workers=1, timeout=TimeOut)
                        output = processor.run_uproot_job({name:files},
                                                          treename='Events',
                                                          processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                               lu=mistag_luts,
                                                                                               extraDaskDirectory = daskDirectory,
                                                                                               ModMass=True, 
                                                                                               RandomDebugMode=False,
                                                                                               BDirect = BDiscDirectory,
                                                                                               bdisc = BDisc,
                                                                                               year=args.year,
                                                                                               apv=convertLabel[VFP],
                                                                                               vfp=VFP,
                                                                                               eras=Letters,
                                                                                               trigs_to_run=Trigs_to_run,
                                                                                               prng=prng),
                                                          executor=processor.dask_executor,
                                                          executor_args={
                                                              'client': client,
                                                              'skipbadfiles':False,
                                                              'schema': BaseSchema},
                                                          chunksize=Chunk[0], maxchunks=Chunk[1])
                        # client.restart()
                    elapsed = time.time() - tstart
                    outputs_weighted[name] = output
                    print(output)
                    if SaveSecondRun:
                        mkdir_p('TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/'
                                  + SaveLocation[name])

                        savefilename = 'TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/' + SaveLocation[name] + name  + '_weighted' + UncType  + SystType + method + TPT + OldDisc + '.coffea'
                        util.save(output, savefilename)
                        print('saving ' + savefilename)


                else: # Run all Root Files
                    if not UsingDaskExecutor:
                        chosen_exec = 'futures'
                        output = processor.run_uproot_job({name:files},
                                                          treename='Events',
                                                          processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                               lu=mistag_luts,
                                                                                               ModMass=True, 
                                                                                               RandomDebugMode=False,
                                                                                               BDirect = BDiscDirectory,
                                                                                               bdisc = BDisc,
                                                                                               year=args.year,
                                                                                               apv=convertLabel[VFP],
                                                                                               vfp=VFP,
                                                                                               eras=Letters,
                                                                                               trigs_to_run=Trigs_to_run,
                                                                                               prng=prng),
                                                          #executor=processor.iterative_executor,
                                                          executor=processor.futures_executor,
                                                          executor_args={
                                                              'skipbadfiles':False,
                                                              'schema': BaseSchema, #NanoAODSchema,
                                                              'workers': 2})

                    else:
                        chosen_exec = 'dask'
                        client.wait_for_workers(n_workers=1, timeout=TimeOut)
                        output = processor.run_uproot_job({name:files},
                                                          treename='Events',
                                                          processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                               lu=mistag_luts,
                                                                                               extraDaskDirectory = daskDirectory,
                                                                                               ModMass=True, 
                                                                                               RandomDebugMode=False,
                                                                                               BDirect = BDiscDirectory,
                                                                                               bdisc = BDisc,
                                                                                               year=args.year,
                                                                                               apv=convertLabel[VFP],
                                                                                               vfp=VFP,
                                                                                               eras=Letters,
                                                                                               trigs_to_run=Trigs_to_run,
                                                                                               prng=prng),
                                                          executor=processor.dask_executor,
                                                          executor_args={
                                                              'client': client,
                                                              'skipbadfiles':False,
                                                              'schema': BaseSchema})
                        # client.restart()
                    elapsed = time.time() - tstart
                    outputs_weighted[name] = output
                    print(output)
                    if SaveSecondRun:
                        mkdir_p('TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/'
                                  + SaveLocation[name])

                        savefilename = 'TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/' + SaveLocation[name] + name  + '_weighted' + UncType + SystType + method + TPT + OldDisc + '.coffea'                    
                        util.save(output, savefilename)
                        print('saving ' + savefilename)
                print('Elapsed time = ', elapsed, ' sec.')
                print('Elapsed time = ', elapsed/60., ' min.')
                print('Elapsed time = ', elapsed/3600., ' hrs.') 

            else:
                continue
        for name,output in outputs_weighted.items(): 
            print("-------Weighted " + name + "--------")
            for i,j in output['cutflow'].items():        
                print( '%20s : %1s' % (i,j) )
        print("\n\nWe\'re done here!!\n")
    else:
        pass

    if args.dask and args.newCluster:
        cluster.close()



    if args.runAMO:
        tstart = time.time()

        outputs_weighted = {}

        seed = 1234577890
        prng = RandomState(seed)

        for name,files in filesets_to_run.items(): 
            if not OnlyCreateLookupTables:
                print('Processing', name)
                if not RunAllRootFiles:
                    if not UsingDaskExecutor:
                        chosen_exec = 'futures'
                        output = processor.run_uproot_job({name:files},
                                                          treename='Events',
                                                          processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                               lu=mistag_luts,
                                                                                               ModMass=False, 
                                                                                               RandomDebugMode=False,
                                                                                               BDirect = BDiscDirectory,
                                                                                               bdisc = BDisc,
                                                                                               year=args.year,
                                                                                               apv=convertLabel[VFP],
                                                                                               vfp=VFP,
                                                                                               eras=Letters,
                                                                                               trigs_to_run=Trigs_to_run,
                                                                                               prng=prng),
                                                          #executor=processor.iterative_executor,
                                                          executor=processor.futures_executor,
                                                          executor_args={
                                                              'skipbadfiles':False,
                                                              'schema': BaseSchema, #NanoAODSchema,
                                                              'workers': 2},
                                                          chunksize=Chunk[0], maxchunks=Chunk[1])
                    else:
                        chosen_exec = 'dask'
                        client.wait_for_workers(n_workers=1, timeout=TimeOut)
                        output = processor.run_uproot_job({name:files},
                                                          treename='Events',
                                                          processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                               lu=mistag_luts,
                                                                                               extraDaskDirectory = daskDirectory,
                                                                                               ModMass=False, 
                                                                                               RandomDebugMode=False,
                                                                                               BDirect = BDiscDirectory,
                                                                                               bdisc = BDisc,
                                                                                               year=args.year,
                                                                                               apv=convertLabel[VFP],
                                                                                               vfp=VFP,
                                                                                               eras=Letters,
                                                                                               trigs_to_run=Trigs_to_run,
                                                                                               prng=prng),
                                                          executor=processor.dask_executor,
                                                          executor_args={
                                                              'client': client,
                                                              'skipbadfiles':False,
                                                              'schema': BaseSchema},
                                                          chunksize=Chunk[0], maxchunks=Chunk[1])
                        # client.restart()
                    elapsed = time.time() - tstart
                    outputs_weighted[name] = output
                    print(output)
                    if SaveSecondRun:
                        mkdir_p('TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/'
                                  + SaveLocation[name])

                        savefilename = 'TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/' + SaveLocation[name] + name  + '_weighted_MistagOnly' + UncType  + SystType + method + TPT + OldDisc + '.coffea'
                        util.save(output, savefilename)
                        print('saving ' + savefilename)


                else: # Run all Root Files
                    if not UsingDaskExecutor:
                        chosen_exec = 'futures'
                        output = processor.run_uproot_job({name:files},
                                                          treename='Events',
                                                          processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                               lu=mistag_luts,
                                                                                               ModMass=False, 
                                                                                               RandomDebugMode=False,
                                                                                               BDirect = BDiscDirectory,
                                                                                               bdisc = BDisc,
                                                                                               year=args.year,
                                                                                               apv=convertLabel[VFP],
                                                                                               vfp=VFP,
                                                                                               eras=Letters,
                                                                                               trigs_to_run=Trigs_to_run,
                                                                                               prng=prng),
                                                          #executor=processor.iterative_executor,
                                                          executor=processor.futures_executor,
                                                          executor_args={
                                                              'skipbadfiles':False,
                                                              'schema': BaseSchema, #NanoAODSchema,
                                                              'workers': 2})

                    else:
                        chosen_exec = 'dask'
                        client.wait_for_workers(n_workers=1, timeout=TimeOut)
                        output = processor.run_uproot_job({name:files},
                                                          treename='Events',
                                                          processor_instance=TTbarResProcessor(UseLookUpTables=True,
                                                                                               lu=mistag_luts,
                                                                                               extraDaskDirectory = daskDirectory,
                                                                                               ModMass=False, 
                                                                                               RandomDebugMode=False,
                                                                                               BDirect = BDiscDirectory,
                                                                                               bdisc = BDisc,
                                                                                               year=args.year,
                                                                                               apv=convertLabel[VFP],
                                                                                               vfp=VFP,
                                                                                               eras=Letters,
                                                                                               trigs_to_run=Trigs_to_run,
                                                                                               prng=prng),
                                                          executor=processor.dask_executor,
                                                          executor_args={
                                                              'client': client,
                                                              'skipbadfiles':False,
                                                              'schema': BaseSchema})
                        # client.restart()
                    elapsed = time.time() - tstart
                    outputs_weighted[name] = output
                    print(output)
                    if SaveSecondRun:
                        mkdir_p('TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/'
                                  + SaveLocation[name])

                        savefilename = 'TTbarAllHadUproot/CoffeaOutputsForCombine/Coffea_SecondRun/' + SaveLocation[name] + name  + '_weighted_MistagOnly' + UncType + SystType + method + TPT + OldDisc + '.coffea'                    
                        util.save(output, savefilename)
                        print('saving ' + savefilename)
                print('Elapsed time = ', elapsed, ' sec.')
                print('Elapsed time = ', elapsed/60., ' min.')
                print('Elapsed time = ', elapsed/3600., ' hrs.') 

            else:
                continue
        for name,output in outputs_weighted.items(): 
            print("-------Weighted " + name + "--------")
            for i,j in output['cutflow'].items():        
                print( '%20s : %1s' % (i,j) )
        print("\n\nWe\'re done here!!\n")
    else:
        pass

    if args.dask and args.newCluster:
        cluster.close()
    print(psutil.Process(os.getpid()).memory_info().rss / 10 ** 6) # Display MB of memory usage
    exit()
    
if __name__ == '__main__':
    main()
