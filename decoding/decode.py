import numpy as np
import h5py
import sys
import decoding
import network
import os
from scipy.special import logsumexp

def softmax(logits):
    dim = len(logits.shape)
    axis_to_sum = dim-1
    return( (np.exp(logits).T / np.sum(np.exp(logits),axis=axis_to_sum).T).T )

def logit_to_log_likelihood(logits):
    # Normalizes logits so they are valid log-likelihoods
    # takes the place of softmax operation in data preprocessing
    dim = len(logits.shape)
    axis_to_sum = dim-1
    return( (logits.T - logsumexp(logits,axis=2).T).T )

def load_logits(file_path, flatten=False):
    #read_raw = np.fromfile(file_path,dtype=np.float32)
    #read_reshape = read_raw.reshape(-1,window,5) # assuming alphabet of 5 and window size of 200
    read_reshape = np.load(file_path)
    if np.isclose(np.sum(read_reshape[0,0]), 1):
        print('WARNING: Logits appear to be probabilities. Taking log.',file=sys.stderr)
        read_reshape = np.log(read_reshape)
    else:
        read_reshape = logit_to_log_likelihood(read_reshape)
    if flatten:
        return(np.concatenate(read_reshape))
    else:
        return(read_reshape)

def trace_from_flappie(p):
    hdf = h5py.File(p, 'r')
    read_id = list(hdf)[0]
    trace = np.array(hdf[read_id]['trace'])
    # signal = np.array(hdf[read_id]['signal'])
    hdf.close()
    return(trace)

def trace_from_guppy(p):
    hdf = h5py.File(p, 'r')
    trace = np.array(hdf['/Analyses/Basecall_1D_000/BaseCalled_template/Trace'])
    hdf.close()
    return(trace)

def model_from_trace(f, basecaller=""):
    # infer model type from file
    file_name, file_extension = os.path.splitext(f)
    if file_extension == '.npy' or basecaller == 'poreover':
        try:
            trace = load_logits(f, flatten=True)
            model = decoding.transducer.poreover(trace)
        except:
            raise
    elif file_extension == '.hdf5' or basecaller == 'flappie':
        try:
            trace = trace_from_flappie(f)
            eps = 0.0000001
            trace = np.log((trace + eps)/(255 + eps))
            model = decoding.transducer.flipflop(trace)
        except:
            raise
    elif file_extension == '.fast5' or basecaller == 'guppy':
        try:
            trace = trace_from_guppy(f)
            eps = 0.0000001
            trace = np.log((trace + eps)/(255 + eps))
            model = decoding.transducer.flipflop(trace)
        except:
            raise
    else:
        if basecaller == "":
            print("Problem loading the trace probabilities, please specify where they came from with --basecaller [poreover/guppy/flappie]")
        else:
            print("Problem loading the trace probabilities")
        sys.exit(1)

    return(model)

def decode(args):
    # load probabilities from running basecaller
    in_path = getattr(args, 'in')
    model = model_from_trace(in_path, args.basecaller)

    # call appropriate decoding function
    sequence = model.viterbi_decode()

    # output decoded sequence
    fasta_header = os.path.basename(in_path)
    if args.out is None:
        fasta_file = sys.stdout
    else:
        fasta_file = open(args.out+'.fasta','a')
    print(network.run_model.fasta_format(fasta_header, sequence), file=fasta_file)
