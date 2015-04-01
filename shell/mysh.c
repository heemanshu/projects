#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#include <unistd.h>
#include <sys/wait.h>

#define bufLen 1024
#define ArgCount 64

char** parseCmd(char* inStr,int* pipecount, int *isSemiColon, char **semiColonIndex)
{ 

  char** args = (char**)malloc(ArgCount*sizeof(char*));	

  int spaces = 0, argc = 0;
  char *prev = inStr, *arg;

  while(*inStr != '\0' && *inStr != '\n' && *inStr != ';') {
	if (*inStr == '|') {
		(*pipecount)++;
		arg = strndup(prev, (inStr - prev));
		if(strlen(arg) != 0)
			args[argc++] = arg;
		args[argc++] = "|";
		inStr++;
		prev = inStr;
		continue;
	}

	if (*inStr == '>') {
		int increment = 1;
		if (*(inStr + increment) == '>')
			increment = 2;
		arg = strndup(prev, (inStr - prev));
		if(strlen(arg) != 0)
			args[argc++] = arg;
		if (increment == 2) {
			args[argc++] = ">>";
			inStr++;
		}
		else 
			args[argc++] = ">";
		inStr++;
		prev = inStr;
		continue;
	}
	if(*inStr == ' ' || *inStr == '\t'){
		while(*inStr == ' ' || *inStr == '\t') {
		++inStr;
		spaces ++;
		}
	    	
		if(*inStr == ';')
			continue;

	    	arg = strndup(prev,(inStr - prev - spaces));
		if(strlen(arg) != 0)
	    		args[argc++] = arg;
	    	prev = inStr;
		spaces = 0;
		continue;
    	}
    
	++inStr;
  }
  
  if(*inStr == '\n' && prev != inStr) {
    arg = strndup(prev,(inStr - prev));
		if(strlen(arg) != 0)
    	args[argc++] = arg;
  }

  if(*inStr == ';') {
    arg = strndup(prev,(inStr - prev - spaces));
    if(strlen(arg) != 0)
	args[argc++] = arg;
    *isSemiColon = 1;
    *semiColonIndex = inStr;
  }
  
  args[argc] = NULL;
  return args;
}

int main()
{
  pid_t pid;
  char in_cmd[bufLen], **args, *ptr = NULL;
  int pipes = 0, isSemiColon = 0;
  while(1) {
	pipes = 0;
	
	if(!isSemiColon) {
 		printf("mysh> ");
		fgets((char *)&in_cmd, bufLen, stdin);
	}
	else {
		strcpy(in_cmd, ptr+1);
		isSemiColon = 0;
	}

	args = parseCmd(in_cmd,&pipes, &isSemiColon, &ptr);
	char buf[100];

	if(args[0] ==NULL)
	continue;

	//cd command
	if(strcmp(args[0], "cd") == 0) {
	
		if(args[1] == NULL)
			args[1] = getenv("HOME");

		if(args[1] == NULL) {
			fprintf(stderr,"Error!\n");
			continue;
		}
		int err = chdir(args[1]);
		if(err == -1) {
			fprintf(stderr,"Error!\n");
		}
		continue;
	}

	//pwd command
	else if(strcmp(args[0], "pwd") == 0) {
		char *cwd;
		if ((cwd = getcwd(NULL, 128)) == NULL) {
			fprintf(stderr,"Error!\n");
			continue;
		}
		printf("%s\n", cwd);
		free(cwd); /* free memory allocated by getcwd() */
		continue;	
	}

	//exit command
	else if(strcmp(args[0], "exit") == 0) {
		if(args[1] == NULL)
			exit(0);
		fprintf(stderr,"Error!\n");
		continue;
	}

	else {
		//pipe and output redirection handling
		int prev = 0, ind = 0, isOpRedirect = 0;
		int fd[pipes+1][2];
		int pipeid = 1;
		int err = pipe(fd[0]);

		while (pipeid < pipes + 1) {
			err = pipe(fd[pipeid]);
			if (err == -1) {
				fprintf(stderr,"Error!\n");
				exit(1);
			}
			pipeid++;
		}
		pipeid = 0;
		char *(str[64]);
		for(; args[ind] != NULL; ++ind) {
			
			if(strcmp(args[ind], "|") == 0 || strcmp(args[ind], ">") == 0 || strcmp(args[ind], ">>") == 0) {
	
		    		if((pid = fork()) == 0) {// child process
    		
					int k = 0;
					if((strcmp(args[ind], ">") == 0 || strcmp(args[ind], ">>") == 0) && args[ind+1] != NULL)
					{
						int ii = prev;
						for(; ii < ind; ++ii)
							str[k++] = strdup(args[ii]);

						for(ii = ind + 2; args[ii] != NULL; ++ii)
							str[k++] = strdup(args[ii]);

						str[k] = NULL;
					}

					else
				 		args[ind] = NULL;

					if(pipeid == 0)
						err = dup2(fd[pipeid][0],0);
					else
						err = dup2( fd[pipeid - 1][0], 0);

					close(fd[pipeid][0]);	
					err = dup2(fd[pipeid][1],1);
					close(fd[pipeid][1]);

					if(k != 0) {
						if (execvp(str[0], &str[0]) == -1)
						{
							fprintf(stderr,"Error!\n");
							exit(EXIT_FAILURE);
						}
					}

					else{
						if (execvp(args[prev], &args[prev]) == -1)
						{
							fprintf(stderr,"Error!\n");
							exit(EXIT_FAILURE);
						}
					}	
			}
    			else if(pid > 0) {// parent process
				prev = ind+1;
				close(fd[pipeid][1]);
				wait(NULL);
				if(args[ind][0] ==  '>') {
					isOpRedirect = 1;
					int bytes = 0;
					int fdWrite;
					
					if(args[ind][1] == '>') {
						fdWrite = open(args[ind+1], O_CREAT | O_RDWR | O_APPEND, 0777);
					}
					else
						fdWrite = open(args[ind+1], O_CREAT | O_WRONLY, 0777);
					
					int rd = 0;
					if(pipeid > 0)
						rd = pipeid;

					while((bytes = read(fd[rd][0], buf, 1)) > 0)
						write(fdWrite, buf, bytes);
				}
			}
			if(!isOpRedirect)
				++pipeid;
		}
	}		


	if(!isOpRedirect) {

	    	if((pid = fork()) == 0) {// child process
			if(pipes > 0) {
				dup2(fd[pipes - 1][0], 0);
				close(fd[pipes - 1][0]);
			}
				
			if (execvp(args[prev], &args[prev]) == -1) {
				fprintf(stderr,"Error!\n");
				exit(EXIT_FAILURE);
			}
				
		}

		else if(pid > 0) {// parent process
      			wait(NULL);
    		}
   	 		
		else { // fork failed
     			fprintf(stderr, "Error!\n");
   		}
	} // end of if !OpRedirect

	}	// end of else !(cd, pwd or exit)

	} // end of while loop

  return 0;
}

