"""Atualização mensal isolada; publica somente após validação de todas as camadas."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,hashlib,json,os,shutil,subprocess,sys,tomllib,uuid
from configuracao import RAIZ,ESTADO,DADOS
from etl.definicao_cid import ID_DEFINICAO_CID
from etl.revisoes import registrar_ciclo
from etl.nucleo_tabnet import URL,write_json
from concurrent.futures import ThreadPoolExecutor

def intervalo(hoje,cfg,inicio=None,fim=None):
    fim=hoje.year if fim is None else fim
    inicio=max(cfg['ano_inicial_historico'],hoje.year-cfg['anos_reprocessamento']+1) if inicio is None else inicio
    if not cfg['ano_inicial_historico']<=inicio<=fim<=hoje.year:raise ValueError('Intervalo de atualização inválido.')
    return inicio,fim

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inicio',type=int);ap.add_argument('--fim',type=int)
    ap.add_argument('--forcar',action='store_true')
    ap.add_argument('--paralelo',action='store_true',help='Consulta base e complementos históricos em paralelo, mantendo a validação final conjunta.')
    ap.add_argument('--retomar-lote',type=Path,help='Reutiliza dados de um lote local interrompido; todas as camadas serão validadas antes de publicar.')
    ap.add_argument('--avaliar',action='store_true',help='Reproduz o experimento estatístico no lote validado antes de publicar os dados.')
    ap.add_argument('--planejar',action='store_true',help='Exibe o plano sem acessar a rede.')
    ap.add_argument('--publicar-local',action='store_true',help='Copia dados validados para o checkout; executar com app local parado.')
    args=ap.parse_args()
    cfg=tomllib.loads((RAIZ/'config.toml').read_text())['atualizacao']
    hoje=datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    inicio,fim=intervalo(hoje,cfg,args.inicio,args.fim)
    anos=[a for a in range(inicio,fim+1) if a<hoje.year or hoje.month>1]
    plano={'inicio':inicio,'fim':fim,'anos_complementos':anos,'motor':cfg['motor'],'estado':str(ESTADO),'publicar_local':args.publicar_local,'paralelo':args.paralelo,'avaliar':args.avaliar}
    if args.planejar:print(json.dumps(plano,ensure_ascii=False,indent=2));return
    if not anos:raise ValueError('Nenhum ano com meses encerrados no intervalo.')
    ESTADO.mkdir(parents=True,exist_ok=True)
    lock=ESTADO/'atualizacao.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(fd,str(os.getpid()).encode());os.close(fd)
    lote=ESTADO/'lotes'/(datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8])
    destino=lote/'dados'
    env=os.environ.copy();env.update(TCC_DADOS_DIR=str(destino),TCC_ETL_RAIZ=str(ESTADO),TCC_TABNET_MOTOR=cfg['motor'],TCC_INTERVALO_SEGUNDOS=str(cfg['intervalo_segundos']))
    report={'plano':plano,'status':'executando','lote':str(lote)}
    def run(*cmd):subprocess.run([sys.executable,*cmd],cwd=RAIZ,env=env,check=True)
    try:
        lote.mkdir(parents=True)
        origem=DADOS
        if args.retomar_lote:
            anterior=args.retomar_lote.resolve()
            if anterior.parent!=(ESTADO/'lotes').resolve() or not (anterior/'execucao.json').is_file():
                raise ValueError('Retomada exige um lote desta instalação com relatório de execução.')
            origem=anterior/'dados';report['retomado_de']=str(anterior)
        shutil.copytree(origem,destino)
        force=['--forcar'] if args.forcar else []
        historicos=[a for a in anos if a<hoje.year]
        if args.paralelo and historicos and not args.retomar_lote:
            # As camadas leem o snapshot inicial; não se incorpora a base enquanto
            # os complementos históricos ainda estão consultando ou gravando arquivos.
            # Cada camada usa evidências/SQLite próprios e um cliente independente.
            with ThreadPoolExecutor(max_workers=3) as executor:
                tarefas=[executor.submit(run,'-m','etl.executar_base','--inicio',str(inicio),'--fim',str(fim),*force)]
                for module in ['extrair_raca_cor','extrair_meios_cid']:
                    tarefas.append(executor.submit(run,'-m','etl.'+module,'--inicio',str(min(historicos)),'--fim',str(max(historicos)),*force))
                # Aguarda e inspeciona todos: qualquer falha impede incorporação/publicação.
                erros=[]
                for tarefa in tarefas:
                    try:tarefa.result()
                    except Exception as exc:erros.append(exc)
                if erros:raise RuntimeError('Extração paralela falhou: '+'; '.join(map(str,erros)))
            run('-m','etl.incorporar_lote',str(ESTADO))
            if hoje.year in anos:
                # O ano corrente depende da cobertura atualizada da base principal.
                for module in ['extrair_raca_cor','extrair_meios_cid']:
                    run('-m','etl.'+module,'--inicio',str(hoje.year),'--fim',str(hoje.year),*force)
        else:
            run('-m','etl.executar_base','--inicio',str(inicio),'--fim',str(fim),*force)
            run('-m','etl.incorporar_lote',str(ESTADO))
            for module,arquivo in [('extrair_raca_cor','raca_cor_meta.json'),('extrair_meios_cid','meios_cid_meta.json')]:
                pendentes=anos
                if args.retomar_lote and not args.forcar:
                    camada=json.loads((destino/arquivo).read_text())
                    pendentes=[a for a in anos if camada.get('definicao_cid_por_ano',{}).get(str(a))!=ID_DEFINICAO_CID
                               or not camada.get('cobertura',{}).get(str(a)) or a==hoje.year]
                for a in pendentes:
                    run('-m','etl.'+module,'--inicio',str(a),'--fim',str(a),*force)
        run('-m','etl.validar','--anos',*[str(a) for a in anos])
        report['status']='validado'
        anos_diagnostico=[a for a in anos if a>=2022]
        if not (destino/'diagnostico_causas.csv').exists():
            anos_diagnostico=list(range(2022,hoje.year+1))
        if anos_diagnostico:
            try:
                run('-m','etl.diagnostico_causas','--anos',*[str(a) for a in anos_diagnostico],
                    '--saida',str(destino),'--evidencias',str(lote/'qualidade_causas'))
                report['diagnostico_causas']={'status':'disponivel','anos_consultados':anos_diagnostico}
            except subprocess.CalledProcessError:
                arq=destino/'diagnostico_causas_meta.json'
                try:camada=json.loads(arq.read_text())
                except (FileNotFoundError,json.JSONDecodeError):camada={}
                camada.update(status='obsoleto' if (destino/'diagnostico_causas.csv').exists() else 'indisponivel',
                              fonte=camada.get('fonte',URL),
                              ultima_tentativa_utc=datetime.now(ZoneInfo('UTC')).isoformat(),
                              erro=camada.get('erro','Processo diagnóstico não concluído; contagens anteriores preservadas.'))
                write_json(arq,camada)
                report['diagnostico_causas']={'status':'indisponivel_ou_obsoleto',
                    'nota':'Falha complementar não altera contagens principais; consulte diagnostico_causas_meta.json.'}
        if args.avaliar:
            resultado=lote/'monitoramento'
            run('-m','experimentos.monitoramento','--saida',str(resultado))
            manifesto=json.loads((resultado/'manifesto.json').read_text())
            if manifesto['sha256_dataset']!=hashlib.sha256((destino/'dataset.zip').read_bytes()).hexdigest():
                raise ValueError('Experimento estatístico não corresponde ao lote validado.')
            report['monitoramento']={'pasta':str(resultado),'sha256_dataset':manifesto['sha256_dataset'],
                                     'referencia':manifesto['referencia'],'parametros':manifesto['parametros']}

        backup=lote/'dados_anteriores';shutil.copytree(DADOS,backup)
        report['snapshots']=registrar_ciclo(lote,ESTADO)
        if args.publicar_local:
            try:
                for file in destino.iterdir():
                    if file.is_file():
                        temp=DADOS/(file.name+'.tmp');shutil.copy2(file,temp);os.replace(temp,DADOS/file.name)
            except BaseException:
                for file in backup.iterdir():shutil.copy2(file,DADOS/file.name)
                raise
            report['status']='publicado_no_checkout'
    except BaseException as exc:
        report['status']='falhou';report['erro']=str(exc);raise
    finally:
        try:
            if lote.exists():
                (lote/'execucao.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        finally:
            lock.unlink(missing_ok=True)
            print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
