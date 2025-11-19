package com.elecciones.backend.service;

import com.elecciones.backend.model.VotoPresidencial;
import com.elecciones.backend.repository.VotoPresidencialRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class VotoPresidencialService {

    private final VotoPresidencialRepository repository;

    public VotoPresidencialService(VotoPresidencialRepository repository) {
        this.repository = repository;
    }

    public List<VotoPresidencial> getAll() {
        return repository.findAll();
    }

    public Optional<VotoPresidencial> getById(UUID id) {
        return repository.findById(id);
    }

    public VotoPresidencial save(VotoPresidencial voto) {
        return repository.save(voto);
    }

    public void delete(UUID id) {
        repository.deleteById(id);
    }
}
